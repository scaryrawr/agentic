---
name: image-gen
description: Use this skill to create, generate, draw, or edit images/photos into saved PNG files with OMLX image models. Covers text-to-image and image-to-image edits. Do not use for text-only image explanations, screenshot summaries, or non-generative image processing scripts.
allowed-tools: Bash(scripts/generate.sh:*) Bash(scripts/edit.sh:*)
---

# OMLX Image Generation and Editing

Generate images from prompts or edit existing images with OMLX/OpenAI-compatible image endpoints.

## Use this skill for

- Text-to-image requests: "generate/create/draw/make an image", product shots, icons, illustrations, PNG artifacts.
- Image edit requests: modify a supplied image/photo, add/remove/change elements, or produce an edited PNG.

Do not use it for text-only image explanations, screenshot summaries, or code that only resizes/processes existing images.

## Requirements

- `$OMLX_BASE_URL` must be set.
- `curl`, `jq`, and `base64` must be available.
- Editing requires a source `.png`, `.jpg`, `.jpeg`, or `.webp` file.

## Workflow

1. Keep user inputs and outputs in the user's workspace. Pass absolute workspace paths for `--input`, `--inputs`, `--mask`, and `--output`.
2. Discover an available model from `$OMLX_BASE_URL/v1/models/status` unless the user specified one. Prefer models whose `capabilities` or `tasks` include `generation` or `edit`, or whose `engine_type`/`model_type` is `image`.
3. Use `scripts/generate.sh` or `scripts/edit.sh`. Do not hard-code install locations, copy scripts elsewhere, or run non-bundled wrappers. The scripts refuse outputs inside the skill directory.
4. Report the saved file path and model used.

## Commands

Generate:

```bash
scripts/generate.sh \
  --prompt "a watercolor fox in a moonlit forest" \
  --model "<image-model>" \
  --size "1024x1024" \
  --output "/absolute/path/to/user/workspace/result.png"
```

Edit:

```bash
scripts/edit.sh \
  --input "/absolute/path/to/user/workspace/source.png" \
  --prompt "add sunglasses" \
  --model "<image-edit-model>" \
  --output "/absolute/path/to/user/workspace/edited.png"
```

Read `references/generation.md` or `references/editing.md` only when you need optional parameters such as `--n`, `--quality`, `--style`, `--mask`, multi-input edits, or URL responses.
