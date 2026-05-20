---
name: image-gen
description: Generate images and edit images using OpenAI-compatible endpoints. Uses $OMLX_BASE_URL for the API base. Supports both generation (/v1/images/generations) and editing (/v1/images/edits) with base64 output. Use when asked to create, generate, produce, or edit images.
---

# OMLX Image Generation & Editing

Generate images from text prompts or edit existing images using OpenAI-compatible endpoints.

## Prerequisites

- Environment variable `$OMLX_BASE_URL` must be set (e.g., `https://api.example.com`)
- `jq` must be installed for JSON parsing
- For editing: a source image file (`.png`, `.jpg`, `.jpeg`)

## Quick Reference

| Operation | Script                | Description                                |
| --------- | --------------------- | ------------------------------------------ |
| Generate  | `scripts/generate.sh` | Create images from text prompts            |
| Edit      | `scripts/edit.sh`     | Edit existing images (with optional masks) |

## Important: output location

- Do **not** `cd` into this skill directory to run the scripts. Treat the skill directory as read-only instructions and tooling.
- Run scripts from the user's workspace/current task directory, or invoke them by absolute path from wherever you already are.
- Prefer an explicit absolute `--output` path outside the skill directory, e.g. `--output "$PWD/result.png"`.
- Never save, copy, or leave generated/edited image files in this skill directory. If an image is accidentally created here, **move** it (`mv`) to the user's requested/workspace location rather than copying it, then verify no duplicate image remains in the skill directory.
- The scripts reject output paths that resolve inside this skill directory.

Example invocation without changing directories:

```bash
~/.agents/skills/omlx-image-gen/scripts/generate.sh \
  --prompt "a watercolor fox in a moonlit forest" \
  --model "<image-model>" \
  --output "$PWD/fox.png"
```

## Generation Workflow

1. From the user's workspace (not the skill directory), run `/Users/mike/.agents/skills/omlx-image-gen/scripts/generate.sh` with a prompt, model, and preferably an absolute `--output` path.
2. The script saves the generated image as a `.png` file at the requested output path, or in the current working directory when `--output` is omitted.
3. See [references/generation.md](references/generation.md) for full parameter details.

## Editing Workflow

1. From the user's workspace (not the skill directory), provide a source image file to `/Users/mike/.agents/skills/omlx-image-gen/scripts/edit.sh`.
2. Optionally provide a mask image for selective edits.
3. The script saves the edited image as a `.png` file at the requested output path, or in the current working directory when `--output` is omitted.
4. See [references/editing.md](references/editing.md) for full parameter details.

## Model Discovery

Available models are listed at `$OMLX_BASE_URL/v1/models/status`. Filter for models with `image` in their name or type. Do not assume what models are available or which mode is best to use.

## Parameters

### Generation (`generate.sh`)

- `--prompt` — Text prompt (required)
- `--model` — Model name (required)
- `--n` — Number of images (default: 1)
- `--size` — Image dimensions, e.g. `1024x1024` (default: `1024x1024`)
- `--response_format` — `b64_json` or `url` (default: `b64_json`)
- `--quality` — `hd`, `standard`, or `quality` (default: `standard`)
- `--style` — `vivid` or `natural` (default: `vivid`)
- `--output` — Output file path. Prefer an absolute path in the user's workspace; paths inside the skill directory are refused.

### Editing (`edit.sh`)

- `--input` — Single source image file (default mode)
- `--inputs` — Multiple source images (overrides `--input`, model-dependent)
- `--prompt` — Edit instructions (required)
- `--model` — Model name (required)
- `--mask` — Mask image file (optional, for selective edits)
- `--n` — Number of images (default: 1)
- `--size` — Output dimensions (default: same as input)
- `--response_format` — `b64_json` or `url` (default: `b64_json`)
- `--output` — Output file path. Prefer an absolute path in the user's workspace; paths inside the skill directory are refused.

## Notes

- All output images are saved as `.png` files at `--output`, or in the current working directory if `--output` is omitted. Output paths inside the skill directory are refused.
- All output images are base64-encoded (as `b64_json` by default).
- Use `--output` to specify a custom filename. Prefer an absolute path in the user's workspace; relative paths resolve against the current working directory.
- The `$OMLX_BASE_URL` environment variable is read from the shell — ensure it is set before running.
- If `$OMLX_BASE_URL` is not set, the scripts print an error and exit with code 1.
- For detailed parameter reference, see the files in `references/`.
