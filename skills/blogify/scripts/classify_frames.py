#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=1.40"]
# ///
"""Classify frames with an OMLX vision model, using constrained JSON output.

The winning technique from practice: don't ask for open-ended captions. Give
the model a SHORT fixed set of enum categories plus one line of context, and
force a structured `{"label": ..., "reason": ...}` reply via JSON mode
(response_format=json_object). This turns the model into a reliable router that
pinpoints specific UIs across a dense frame sample.

Note: the OMLX endpoint honors `response_format={"type":"json_object"}` (JSON
mode) but NOT strict `json_schema`, so we validate the label against the enum
ourselves (falling back to OTHER on anything unexpected).

Usage:
  uv run scripts/classify_frames.py \
    --frames-dir /abs/frames_dedup --output /abs/manifest.json \
    --context "screen recording of a talk about CLI tools" \
    --categories "TERMINAL,SLIDE,BROWSER,TALKING_HEAD,OTHER" \
    --select-dir /abs/selected

Env: OMLX_BASE_URL (required), OMLX_API_KEY (optional)
Dependencies: uv, ffmpeg not needed here.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ValidationError

SKILL_ROOT = Path(__file__).resolve().parent.parent


def resolve_output_path(value: str, flag: str, *, is_dir: bool = False) -> Path:
    """Resolve an output path and reject writes inside the skill bundle."""
    path = Path(value).expanduser()
    if not path.is_absolute():
        sys.exit(f"error: {flag} must be an absolute path")
    resolved = path.resolve()
    if resolved == SKILL_ROOT or SKILL_ROOT in resolved.parents:
        sys.exit(f"error: {flag} must be outside the skill")
    return resolved


class Classification(BaseModel):
    label: str
    reason: str = ""


class ClassificationError(RuntimeError):
    """Raised when a frame cannot be classified after model retries."""


def discover_vision_model(client: OpenAI) -> str:
    """Pick a vision model. All Gemma variants accept images; prefer the
    efficient multimodal ones (12B/E4B/E2B), then any Gemma, then other VLMs.
    The larger Gemma models (26B+) only lack video/audio, not image, input."""
    ids = [m.id for m in client.models.list().data]
    non_assistant = [i for i in ids if "assistant" not in i.lower()]

    def first_with(terms, pool):
        return next((i for i in pool if any(t in i.lower() for t in terms)), None)

    gemmas = [i for i in non_assistant if "gemma" in i.lower()]
    return (
        first_with(("12b", "e4b", "e2b"), gemmas)
        or (gemmas[0] if gemmas else None)
        or first_with(("vl", "vision", "llava", "pixtral", "internvl"), non_assistant)
        or ""
    )


def build_prompt(context: str, categories: list[str]) -> str:
    cats = ", ".join(categories)
    ctx = f" Context: {context}." if context else ""
    return (
        "You are classifying a single frame from a screen recording."
        f"{ctx} Choose the single best label from this fixed set: {cats}. "
        "Use the OTHER/NONE bucket for blurry, transition, talking-head, or "
        "otherwise non-useful frames. Respond ONLY as JSON of the form "
        '{"label": "<one label>", "reason": "<short reason>"}.'
    )


def fallback_label(categories: list[str]) -> str:
    """Return the enum bucket for unusable frames, or exit if none is configured."""
    for preferred in ("OTHER", "NONE"):
        match = next((c for c in categories if c.lower() == preferred.lower()), None)
        if match:
            return match
    sys.exit("error: --categories must include OTHER or NONE")


def classify_one(client, model, prompt, categories, fallback, frame: Path):
    data_uri = "data:image/jpeg;base64," + base64.b64encode(frame.read_bytes()).decode()
    label, reason = fallback, ""
    try:
        resp = client.chat.completions.create(
            model=model,
            max_tokens=200,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                }
            ],
        )
        content = resp.choices[0].message.content or "{}"
        parsed = Classification.model_validate_json(content)
        # Validate the label against the enum (case-insensitive); else fallback.
        match = next((c for c in categories if c.lower() == parsed.label.strip().lower()), None)
        label = match or fallback
        reason = parsed.reason
    except (ValidationError, json.JSONDecodeError):
        reason = "unparseable response"
    except Exception as exc:  # network / server errors after retries
        raise ClassificationError(f"{frame.name}: {exc}") from exc
    return frame, label, reason


def parse_ts(name: str) -> str:
    # frames from sample_frames.sh are named t_<MMmSSs>_f####.jpg
    stem = name
    if stem.startswith("t_") and "_f" in stem:
        return stem[2:].split("_f", 1)[0]
    return ""


def main():
    ap = argparse.ArgumentParser(description="Classify frames via OMLX vision model.")
    ap.add_argument("--frames-dir", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--model", default="")
    ap.add_argument("--context", default="")
    ap.add_argument("--categories", default="USEFUL,OTHER")
    ap.add_argument("--select-dir", default="")
    ap.add_argument("--concurrency", type=int, default=2)
    args = ap.parse_args()

    base_url = os.environ.get("OMLX_BASE_URL")
    if not base_url:
        sys.exit("error: OMLX_BASE_URL must be set")
    frames_dir = Path(args.frames_dir)
    if not frames_dir.is_dir():
        sys.exit("error: --frames-dir not found")
    frames_dir = frames_dir.resolve()
    output = resolve_output_path(args.output, "--output")
    select_dir = resolve_output_path(args.select_dir, "--select-dir", is_dir=True) if args.select_dir else None
    if select_dir and select_dir == frames_dir:
        sys.exit("error: --select-dir must differ from --frames-dir")

    categories = [c.strip() for c in args.categories.split(",") if c.strip()]
    fallback = fallback_label(categories)
    client = OpenAI(
        base_url=f"{base_url.rstrip('/')}/v1",
        api_key=os.environ.get("OMLX_API_KEY", "none"),
        max_retries=4,
        timeout=120,
    )
    model = args.model or discover_vision_model(client)
    if not model:
        sys.exit("error: no vision model found; pass --model")
    print(f"vision model: {model} | categories: {', '.join(categories)}", file=sys.stderr)

    prompt = build_prompt(args.context, categories)
    frames = sorted(frames_dir.glob("*.jpg"))
    if not frames:
        sys.exit("error: no .jpg frames in --frames-dir")

    output.parent.mkdir(parents=True, exist_ok=True)
    if select_dir:
        select_dir.mkdir(parents=True, exist_ok=True)
        for stale in select_dir.glob("*.jpg"):
            stale.unlink()

    manifest = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = [pool.submit(classify_one, client, model, prompt, categories, fallback, f) for f in frames]
        for fut in futures:
            frame, label, reason = fut.result()
            manifest.append({"file": frame.name, "ts": parse_ts(frame.name), "label": label, "reason": reason})
            print(f"  {frame.name} -> {label}", file=sys.stderr)
            if select_dir and label.upper() not in ("OTHER", "NONE"):
                shutil.copy(frame, select_dir / frame.name)

    manifest.sort(key=lambda row: row["file"])
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    counts: dict[str, int] = {}
    for row in manifest:
        counts[row["label"]] = counts.get(row["label"], 0) + 1
    print(f"classified {len(manifest)} frames -> {output}", file=sys.stderr)
    for label, n in sorted(counts.items()):
        print(f"  {n:4d} {label}", file=sys.stderr)


if __name__ == "__main__":
    main()
