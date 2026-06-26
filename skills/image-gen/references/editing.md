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
| `--size` | same as input | Output dimensions. Use `auto` to let the model decide, or `WIDTHxHEIGHT` (e.g. `1024x1024`). |
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
scripts/edit.sh \
  --input "/absolute/path/to/user/workspace/photo.png" \
  --prompt "add sunglasses to the person" \
  --model "omlx-dall-e-edit" \
  --output "/absolute/path/to/user/workspace/photo-sunglasses.png"
```

### Selective edit with mask
```bash
scripts/edit.sh \
  --input "/absolute/path/to/user/workspace/photo.png" \
  --prompt "replace the sky with a sunset" \
  --mask "/absolute/path/to/user/workspace/sky_mask.png" \
  --model "omlx-dall-e-edit" \
  --output "/absolute/path/to/user/workspace/edited.png"
```

### Multiple variations
```bash
scripts/edit.sh \
  --input "/absolute/path/to/user/workspace/photo.png" \
  --prompt "change background to a beach" \
  --model "omlx-dall-e-edit" \
  --n 3 \
  --response_format b64_json \
  --output "/absolute/path/to/user/workspace/beach.png"
```

## Multi-Input Edits

Some models support multiple input images (`--inputs`). The prompt applies across all inputs.

```bash
scripts/edit.sh \
  --inputs "/absolute/path/to/user/workspace/photo1.png" "/absolute/path/to/user/workspace/photo2.png" "/absolute/path/to/user/workspace/photo3.png" \
  --prompt "combine these into a collage" \
  --model "omlx-multi-edit" \
  --output "/absolute/path/to/user/workspace/collage.png"
```

- `--inputs` accepts one or more filenames (separated by spaces)
- `--inputs` overrides `--input` when both are provided
- Model support for multiple inputs varies — check model docs

## Model Discovery

Available models are listed at `$OMLX_BASE_URL/v1/models/status`. Prefer models whose `capabilities` or `tasks` include `edit` for image edits.

## Tips

- Use `scripts/edit.sh` and absolute paths for user workspace inputs and outputs.
- Keep prompts concise — describe what to add, remove, or change.
- For selective edits, provide a mask where white = edited area.
- The mask should match the input image dimensions.
- Use `response_format=url` if you prefer URLs over base64 encoding.
