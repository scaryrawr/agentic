#!/usr/bin/env bash
# edit.sh — Edit images via OpenAI-compatible endpoint
#
# Usage:
#   # Single input (standard)
#   scripts/edit.sh \
#     --input "/path/to/workspace/photo.png" --prompt "add sunglasses" --model "omlx-dall-e-edit" \
#     --output "/path/to/workspace/photo-sunglasses.png"
#
#   # Multiple inputs (if supported by the model)
#   scripts/edit.sh \
#     --inputs "/path/to/workspace/photo1.png" "/path/to/workspace/photo2.png" --prompt "merge these" \
#     --model "omlx-multi-edit" --output "/path/to/workspace/merged.png"
#
# Options:
#   --input FILE           Single source image (default mode)
#   --inputs FILES...      Multiple source images (overrides --input)
#   --prompt TEXT          Edit instructions (required)
#   --model TEXT           Model name (required)
#   --mask FILE            Mask image (optional, for selective edits)
#   --n NUM                Number of images (default: 1)
#   --size WIDTHxHEIGHT    Output dimensions (default: same as input)
#   --response_format      b64_json or url (default: b64_json)
#   --output FILE          Output file (default: edited_<model>.png; must be outside skill dir)
#   --help                 Show this help message
#
# Dependencies: jq, curl, base64

set -euo pipefail

# Resolve paths. Skill files are read-only runtime assets; edited images must not be written here.
CWD=$(pwd -P)
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SKILL_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd -P)

resolve_output_path() {
  local out="$1"
  if [[ "$out" != /* ]]; then
    out="${CWD}/${out}"
  fi

  local out_dir out_base probe suffix canon_dir
  out_dir=$(dirname -- "$out")
  out_base=$(basename -- "$out")
  probe="$out_dir"
  suffix=""

  # Resolve through the nearest existing parent without creating directories first.
  while [[ ! -d "$probe" && "$probe" != "/" ]]; do
    suffix="/$(basename -- "$probe")${suffix}"
    probe=$(dirname -- "$probe")
  done

  canon_dir="$(cd -- "$probe" && pwd -P)${suffix}"
  printf '%s/%s\n' "$canon_dir" "$out_base"
}

ensure_output_outside_skill() {
  local out="$1"
  case "$out" in
    "$SKILL_ROOT"|"$SKILL_ROOT"/*)
      {
        echo "Error: refusing to write edited images inside the skill directory:"
        echo "  $out"
        echo "Pass --output with an absolute path outside the skill directory, e.g.:"
        echo "  scripts/edit.sh --output \"/path/to/workspace/edited.png\" ..."
      } >&2
      exit 1
      ;;
  esac
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Error: required command '$1' not found." >&2
    exit 1
  fi
}

for cmd in curl jq base64; do
  require_command "$cmd"
done

# Defaults
INPUT=""
INPUTS=()
PROMPT=""
MODEL=""
MASK=""
N=1
SIZE=""
RESPONSE_FORMAT="b64_json"
OUTPUT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input)           INPUT="$2";         shift 2 ;;
    --inputs)          shift; while [[ $# -gt 0 && ! "$1" =~ ^-- ]]; do INPUTS+=("$1"); shift; done ;;
    --prompt)          PROMPT="$2";       shift 2 ;;
    --model)           MODEL="$2";        shift 2 ;;
    --mask)            MASK="$2";         shift 2 ;;
    --n)               N="$2";            shift 2 ;;
    --size)            SIZE="$2";         shift 2 ;;
    --response_format) RESPONSE_FORMAT="$2"; shift 2 ;;
    --output)          OUTPUT="$2";       shift 2 ;;
    --help)
      echo "Usage: $0 --input FILE --prompt \"...\" --model \"...\" [options]"
      echo "       $0 --inputs FILE1 FILE2 ... --prompt \"...\" --model \"...\" [options]"
      echo ""
      echo "Edit one or more images using OpenAI-compatible endpoint."
      echo ""
      echo "Options:"
      echo "  --input FILE           Single source image (default mode)"
      echo "  --inputs FILES...      Multiple source images (overrides --input)"
      echo "  --prompt TEXT          Edit instructions (required)"
      echo "  --model TEXT           Model name (required)"
      echo "  --mask FILE            Mask image (optional)"
      echo "  --n NUM                Number of images (default: 1)"
      echo "  --size WxH             Output dimensions (default: same as input)"
      echo "  --response_format      b64_json | url (default: b64_json)"
      echo "  --output FILE          Output file (default: edited_<model>.png; must be outside skill dir)"
      echo "  --help                 Show this help message"
      exit 0
      ;;
    *) echo "Error: Unknown option '$1'. Use --help for usage." >&2; exit 1 ;;
  esac
done

# Validate required fields
if [[ -z "$PROMPT" ]]; then
  echo "Error: --prompt is required." >&2
  exit 1
fi
if [[ -z "$MODEL" ]]; then
  echo "Error: --model is required." >&2
  exit 1
fi

# Determine input files
if [[ ${#INPUTS[@]} -gt 0 ]]; then
  # Multiple inputs mode
  INPUT_FILES=("${INPUTS[@]}")
elif [[ -n "$INPUT" ]]; then
  # Single input mode
  INPUT_FILES=("$INPUT")
else
  echo "Error: --input or --inputs is required." >&2
  exit 1
fi

# Verify all input files exist
for f in "${INPUT_FILES[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "Error: Input file '$f' not found." >&2
    exit 1
  fi
done

# Read base URL from environment
BASE_URL="${OMLX_BASE_URL:?Error: \$OMLX_BASE_URL environment variable must be set.}"
BASE_URL="${BASE_URL%/}"

image_mime_type() {
  case "${1##*.}" in
    png|PNG) echo "image/png" ;;
    jpg|JPG|jpeg|JPEG) echo "image/jpeg" ;;
    webp|WEBP) echo "image/webp" ;;
    *) echo "image/png" ;;
  esac
}

# Convert input files to data-URI image references for the JSON edit API.
INPUT_B64_ARRAY="[]"
for f in "${INPUT_FILES[@]}"; do
  B64=$(base64 < "$f" | tr -d '\n')
  MIME=$(image_mime_type "$f")
  INPUT_B64_ARRAY=$(echo "$INPUT_B64_ARRAY" | jq --arg v "$B64" --arg mime "$MIME" '. + [{image_url: ("data:" + $mime + ";base64," + $v)}]')
done

# Convert mask to a data-URI image reference if provided.
MASK_DATA_URI=""
if [[ -n "$MASK" ]]; then
  if [[ ! -f "$MASK" ]]; then
    echo "Error: Mask file '$MASK' not found." >&2
    exit 1
  fi
  MASK_B64=$(base64 < "$MASK" | tr -d '\n')
  MASK_MIME=$(image_mime_type "$MASK")
  MASK_DATA_URI="data:${MASK_MIME};base64,${MASK_B64}"
fi

# Build output file path (absolute, relative paths resolve against CWD)
if [[ -z "$OUTPUT" ]]; then
  OUTPUT="edited_${MODEL}.png"
fi
OUTPUT=$(resolve_output_path "$OUTPUT")
ensure_output_outside_skill "$OUTPUT"
mkdir -p -- "$(dirname -- "$OUTPUT")"

# Build JSON body
if [[ -n "$MASK_DATA_URI" ]]; then
  # Include mask field
  JSON_BODY=$(jq -n \
    --argjson inputs "$INPUT_B64_ARRAY" \
    --arg prompt "$PROMPT" \
    --arg model "$MODEL" \
    --argjson n "$N" \
    --arg size "$SIZE" \
    --arg response_format "$RESPONSE_FORMAT" \
    --arg mask "$MASK_DATA_URI" \
    '{
      prompt: $prompt,
      model: $model,
      images: $inputs,
      n: $n,
      size: $size,
      response_format: $response_format,
      mask: {image_url: $mask}
    }')
else
  # Without mask
  JSON_BODY=$(jq -n \
    --argjson inputs "$INPUT_B64_ARRAY" \
    --arg prompt "$PROMPT" \
    --arg model "$MODEL" \
    --argjson n "$N" \
    --arg size "$SIZE" \
    --arg response_format "$RESPONSE_FORMAT" \
    '{
      prompt: $prompt,
      model: $model,
      images: $inputs,
      n: $n,
      size: $size,
      response_format: $response_format
    }')
fi

# Make API call
RESPONSE=$(curl -s -X POST "${BASE_URL}/v1/images/edits" \
  -H "Content-Type: application/json" \
  -d "$JSON_BODY")

# Handle response
if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
  echo "Error from image edit API:" >&2
  echo "$RESPONSE" | jq -r '.error.message // .error // .' >&2
  exit 1
fi

if [[ "$RESPONSE_FORMAT" == "b64_json" ]]; then
  DATA_LEN=$(echo "$RESPONSE" | jq '(.data // []) | length')
  if [[ "$DATA_LEN" -lt 1 ]]; then
    echo "Error: image edit API response did not contain any data." >&2
    echo "$RESPONSE" >&2
    exit 1
  fi

  for i in $(seq 0 $((DATA_LEN - 1))); do
    B64=$(echo "$RESPONSE" | jq -r ".data[$i].b64_json // empty")
    if [[ -z "$B64" ]]; then
      echo "Error: image edit API response data[$i] did not include b64_json." >&2
      echo "$RESPONSE" >&2
      exit 1
    fi

    if [[ $DATA_LEN -gt 1 ]]; then
      OUT_FILE="${OUTPUT%.png}_${i}.png"
    else
      OUT_FILE="$OUTPUT"
    fi
    ensure_output_outside_skill "$OUT_FILE"

    echo "$B64" | base64 -d > "$OUT_FILE"
    echo "Saved: $OUT_FILE" >&2
  done
elif [[ "$RESPONSE_FORMAT" == "url" ]]; then
  URL=$(echo "$RESPONSE" | jq -r '.data[0].url')
  ensure_output_outside_skill "$OUTPUT"
  curl -s -o "$OUTPUT" "$URL"
  echo "Saved: $OUTPUT" >&2
else
  echo "Error: Unknown response_format '$RESPONSE_FORMAT'." >&2
  exit 1
fi
