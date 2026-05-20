# Image Editing Reference

Detailed parameters for the `edit.sh` script.

## Parameters

### Required
| Parameter | Description |
|-----------|-------------|
| `--input` | Single source image (`.png`, `.jpg`, `.jpeg`) — default mode |
| `--inputs` | Multiple source images (overrides `--input`, model-dependent) |
| `--prompt` | Instructions for editing the image |
| `--model` | Model name (e.g., `omlx-dall-e-edit`) |

### Optional
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mask` | — | Mask image for selective edits (white = edited area) |
| `--n` | `1` | Number of edited images (1–4) |
| `--size` | same as input | Output dimensions |
| `--response_format` | `b64_json` | `b64_json` returns base64, `url` returns URLs |
| `--output` | `edited_<model>.png` | Output file path. Prefer an absolute path in the user's workspace; paths inside the skill directory are refused. |

## Mask Format

When using `--mask`:
- White pixels (`#ffffff`) indicate the edited area
- Black pixels (`#000000`) are preserved
- Grayscale values are partially edited
- Must be the same dimensions as the input image

## Examples

### Simple edit
```bash
SKILL_ROOT="$HOME/.agents/skills/image-gen"
"$SKILL_ROOT/scripts/edit.sh" \
  --input "$PWD/photo.png" \
  --prompt "add sunglasses to the person" \
  --model "omlx-dall-e-edit" \
  --output "$PWD/photo-sunglasses.png"
```

### Selective edit with mask
```bash
SKILL_ROOT="$HOME/.agents/skills/image-gen"
"$SKILL_ROOT/scripts/edit.sh" \
  --input "$PWD/photo.png" \
  --prompt "replace the sky with a sunset" \
  --mask "$PWD/sky_mask.png" \
  --model "omlx-dall-e-edit" \
  --output "$PWD/edited.png"
```

### Multiple variations
```bash
SKILL_ROOT="$HOME/.agents/skills/image-gen"
"$SKILL_ROOT/scripts/edit.sh" \
  --input "$PWD/photo.png" \
  --prompt "change background to a beach" \
  --model "omlx-dall-e-edit" \
  --n 3 \
  --response_format b64_json \
  --output "$PWD/beach.png"
```

## Multi-Input Edits

Some models support multiple input images (`--inputs`). The prompt applies across all inputs.

```bash
SKILL_ROOT="$HOME/.agents/skills/image-gen"
"$SKILL_ROOT/scripts/edit.sh" \
  --inputs "$PWD/photo1.png" "$PWD/photo2.png" "$PWD/photo3.png" \
  --prompt "combine these into a collage" \
  --model "omlx-multi-edit" \
  --output "$PWD/collage.png"
```

- `--inputs` accepts one or more filenames (separated by spaces)
- `--inputs` overrides `--input` when both are provided
- Model support for multiple inputs varies — check model docs

## Model Discovery

Available models are listed at `$OMLX_BASE_URL/v1/models/status`. Prefer models whose `capabilities` or `tasks` include `edit` for image edits.

## Tips

- Do not `cd` into the skill directory; invoke the script by absolute path and write outputs to the user's workspace.
- Keep prompts concise — describe what to add, remove, or change.
- For selective edits, provide a mask where white = edited area.
- The mask should match the input image dimensions.
- Use `response_format=url` if you prefer URLs over base64 encoding.
