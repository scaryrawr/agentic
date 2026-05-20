#!/usr/bin/env bash
# edit.sh — Edit images via OpenAI-compatible endpoint
#
# Usage (do not cd into the skill directory):
#   # Single input (standard)
#   /Users/mike/.agents/skills/omlx-image-gen/scripts/edit.sh \
#     --input "$PWD/photo.png" --prompt "add sunglasses" --model "omlx-dall-e-edit" \
#     --output "$PWD/photo-sunglasses.png"
#
#   # Multiple inputs (if supported by the model)
#   /Users/mike/.agents/skills/omlx-image-gen/scripts/edit.sh \
#     --inputs "$PWD/photo1.png" "$PWD/photo2.png" --prompt "merge these" \
#     --model "omlx-multi-edit" --output "$PWD/merged.png"
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
        echo "Run this script from the user's workspace without cd'ing to the skill directory,"
        echo "or pass --output with an absolute path outside it, e.g.:"
        echo "  ${SCRIPT_DIR}/edit.sh --output \"\${PWD}/edited.png\" ..."
      } >&2
      exit 1
      ;;
  esac
}

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

# Convert input files to base64 array
INPUT_B64_ARRAY="[]"
for f in "${INPUT_FILES[@]}"; do
  B64=$(base64 < "$f" | tr -d '\n')
  INPUT_B64_ARRAY=$(echo "$INPUT_B64_ARRAY" | jq --arg v "$B64" '. + [$v]')
done

# Convert mask to base64 if provided
MASK_B64=""
if [[ -n "$MASK" && -f "$MASK" ]]; then
  MASK_B64=$(base64 < "$MASK" | tr -d '\n')
fi

# Build output file path (absolute, relative paths resolve against CWD)
if [[ -z "$OUTPUT" ]]; then
  OUTPUT="edited_${MODEL}.png"
fi
OUTPUT=$(resolve_output_path "$OUTPUT")
ensure_output_outside_skill "$OUTPUT"
mkdir -p -- "$(dirname -- "$OUTPUT")"

# Build JSON body
if [[ -n "$MASK_B64" ]]; then
  # Include mask field
  JSON_BODY=$(jq -n \
    --argjson inputs "$INPUT_B64_ARRAY" \
    --arg prompt "$PROMPT" \
    --arg model "$MODEL" \
    --argjson n "$N" \
    --arg size "$SIZE" \
    --arg response_format "$RESPONSE_FORMAT" \
    --arg mask "$MASK_B64" \
    '{
      prompt: $prompt,
      model: $model,
      input: $inputs,
      n: $n,
      size: $size,
      response_format: $response_format,
      mask: $mask
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
      input: $inputs,
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
if [[ "$RESPONSE_FORMAT" == "b64_json" ]]; then
  DATA_LEN=$(echo "$RESPONSE" | jq '.data | length')

  for i in $(seq 0 $((DATA_LEN - 1))); do
    B64=$(echo "$RESPONSE" | jq -r ".data[$i].b64_json")

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
