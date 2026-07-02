# Frames & screenshots

Operational details for `sample_frames.sh`, `dedupe_frames.sh`,
`classify_frames.py`, and `crop_frames.sh`.

## Frame extraction policy

Extract frames and classify them as images. Direct `input_video` is experimental
for real screen recordings and has produced hallucinated or degenerate output in
testing; the same moments were reliable as still images. Direct audio input is
also not part of this workflow; use the transcription pipeline instead.

## Use the vision model as a *classifier*, not a captioner

Avoid open-ended prompts ("describe this / is it useful?"). Use:

- Give the model a **short, fixed set of enum categories** relevant to the
  video (e.g. `TERMINAL,SLIDE,BROWSER,DIALOG,TALKING_HEAD,OTHER`).
- Give it **one line of context** about what the recording is.
- Ask for **exactly one label + a brief reason**, nothing else.

This turns the model into a router that can pinpoint a *specific* UI (a diff
view vs a slide vs a browser) across a dense frame sample far more reliably than
you could by eyeballing hundreds of frames. `classify_frames.py` implements
this; pass `--categories` and `--context`.

It also uses **constrained JSON output** (`response_format={"type":
"json_object"}`) and validates the returned label against the enum with Pydantic.
Note: the OMLX endpoint honors JSON *mode* but not strict `json_schema` or
`guided_choice`, so JSON mode + a schema described in the prompt + local
validation is the reliable combination. This eliminates fragile text parsing and
handles reasoning-style models that would otherwise emit label-less prose.

Always include an `OTHER`/`NONE` bucket so junk (blurry, transition,
talking-head, title-only) has somewhere to go.

## The sampling pitfall that cost real time

Scene detection with a **high threshold silently skips content.** A first pass
at `scene>0.3` missed an entire diff/terminal demo because the on-screen change
between frames was gradual. Fixes, in order:

1. **Sample low + periodic.** `sample_frames.sh` defaults to `scene>0.06` plus a
   frame every `--every 4` seconds, so static slides (no scene change at all)
   are still captured.
2. **Dedupe, then classify.** Low thresholds produce many near-duplicates
   (scrolls, cursor moves). `dedupe_frames.sh` removes consecutive near-dups via
   RMSE so you spend fewer (slower) vision calls.
3. **Targeted re-sampling.** If the transcript says an important demo happens
   around 34–38 min but you have no good frame, re-run `sample_frames.sh
   --start 2040 --end 2320 --scene 0.05` on just that window and classify again.

## Timestamps

`sample_frames.sh` names frames `t_<MMmSSs>_f<index>.jpg` using the real
`pts_time` parsed from ffmpeg's `showinfo` filter, so filenames are on the video
timeline and line up with transcript timestamps. Use `--start` to keep
timestamps correct when sampling a sub-window (the offset is added back).

## Getting publish-quality images

- **Re-extract at full resolution.** Sampled frames are downscaled for triage.
  Once you know the exact second, pull a crisp frame:
  `scripts/extract_frame.sh --input <video> --second <secs> --output <dir>/out.png`.
- **Crop overlays.** Call-shared recordings carry a participant filmstrip (right
  edge) and OS taskbar (bottom). `crop_frames.sh --crop 1680x1040+0+0` removes
  both from 1920×1080 frames. Note: if the filmstrip overlaps app content, that
  content is unrecoverable — pick a frame where it does not, or accept the crop.
- **Verify before publishing.** The classifier occasionally mislabels a desktop
  app as "browser/PR". Always eyeball final picks; a contact sheet
  (`magick montage frames/*.jpg -tile 5x -geometry 320x180 sheet.jpg`) makes
  review fast.

## Concurrency

Vision calls are much heavier than ASR. Run the classifier sequentially (its
default) or at most 1–2 in parallel; pushing harder mostly adds latency.

## Model selection

`classify_frames.py` auto-discovers a model from `/v1/models`. **All Gemma
variants accept image input**, so any of them can classify frames; the larger
Gemma models (26B+) only lack *video/audio* support, which this skill doesn't
use (we send individual extracted frames). The script prefers the efficient
multimodal variants (`12b`/`e4b`/`e2b`), then any other Gemma, then common VLM
ids (`vl`, `vision`, `llava`, `pixtral`, `internvl`). Override with `--model`.
`/v1/models` only lists ids, so if you pass `--model` yourself, confirm it
actually accepts images.

In testing, **gemma-4-12B clearly beat Qwen3.5-9B** for this frame-
classification task: gemma scored 5–6/6 on a labeled set at ~1.2 s/frame with
clean terse labels, while Qwen3.5-9B (a reasoning-style VLM that "thinks out
loud") managed ~2/6, took 9–18 s/frame, and returned label-less prose that
needed extra parsing. Prefer a compact instruct VLM like gemma over a
reasoning VLM for terse, high-volume classification.
