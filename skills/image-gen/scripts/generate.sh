#!/usr/bin/env bash
# generate.sh — Generate images from text prompts via OpenAI-compatible endpoint
#
# Usage:
#   scripts/generate.sh \
#     --prompt "a cat on a mat" --model "omlx-dall-e-3" --output "/path/to/workspace/cat.png"
#
# Options:
#   --prompt TEXT        Text prompt (required)
#   --model TEXT         Model name (required)
#   --n NUM              Number of images to generate (default: 1)
#   --size WIDTHxHEIGHT  Image dimensions (default: 1024x1024)
#   --response_format    Output format: b64_json or url (default: b64_json)
#   --quality            Quality: hd, standard, quality (default: standard)
#   --style              Style: vivid, natural (default: vivid)
#   --output FILE        Output file (default: generated_<model>_<n>.png; must be outside skill dir)
#   --help               Show this help message
#
# Dependencies: jq, curl, base64

set -euo pipefail

# Resolve paths. Skill files are read-only runtime assets; generated images must not be written here.
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
        echo "Error: refusing to write generated images inside the skill directory:"
        echo "  $out"
        echo "Pass --output with an absolute path outside the skill directory, e.g.:"
        echo "  scripts/generate.sh --output \"/path/to/workspace/image.png\" ..."
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
PROMPT=""
MODEL=""
N=1
SIZE="1024x1024"
RESPONSE_FORMAT="b64_json"
QUALITY="standard"
STYLE="vivid"
OUTPUT=""

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prompt)    PROMPT="$2";      shift 2 ;;
    --model)     MODEL="$2";       shift 2 ;;
    --n)         N="$2";           shift 2 ;;
    --size)      SIZE="$2";        shift 2 ;;
    --response_format) RESPONSE_FORMAT="$2"; shift 2 ;;
    --quality)   QUALITY="$2";     shift 2 ;;
    --style)     STYLE="$2";       shift 2 ;;
    --output)    OUTPUT="$2";      shift 2 ;;
    --help)
      echo "Usage: $0 --prompt \"...\" --model \"...\" [options]"
      echo ""
      echo "Generate images from a text prompt using OpenAI-compatible endpoint."
      echo ""
      echo "Options:"
      echo "  --prompt TEXT        Text prompt (required)"
      echo "  --model TEXT         Model name (required)"
      echo "  --n NUM              Number of images (default: 1)"
      echo "  --size WxH           Image dimensions (default: 1024x1024)"
      echo "  --response_format    b64_json | url (default: b64_json)"
      echo "  --quality            hd | standard | quality (default: standard)"
      echo "  --style              vivid | natural (default: vivid)"
      echo "  --output FILE        Output file (default: generated_<model>_<n>.png; must be outside skill dir)"
      echo "  --help               Show this help message"
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

# Read base URL from environment
BASE_URL="${OMLX_BASE_URL:?Error: \$OMLX_BASE_URL environment variable must be set.}"
# Strip trailing slash if present
BASE_URL="${BASE_URL%/}"

# Build output file path (absolute, relative paths resolve against CWD)
if [[ -z "$OUTPUT" ]]; then
  OUTPUT="generated_${MODEL}_${N}.png"
fi
OUTPUT=$(resolve_output_path "$OUTPUT")
ensure_output_outside_skill "$OUTPUT"
mkdir -p -- "$(dirname -- "$OUTPUT")"

# Build JSON body
JSON_BODY=$(jq -n \
  --arg prompt "$PROMPT" \
  --arg model "$MODEL" \
  --argjson n "$N" \
  --arg size "$SIZE" \
  --arg response_format "$RESPONSE_FORMAT" \
  --arg quality "$QUALITY" \
  --arg style "$STYLE" \
  '{
    prompt: $prompt,
    model: $model,
    n: $n,
    size: $size,
    response_format: $response_format,
    quality: $quality,
    style: $style
  }')

# Make API call
RESPONSE=$(curl -s -X POST "${BASE_URL}/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d "$JSON_BODY")

# Extract results based on response format
if echo "$RESPONSE" | jq -e '.error' >/dev/null 2>&1; then
  echo "Error from image generation API:" >&2
  echo "$RESPONSE" | jq -r '.error.message // .error // .' >&2
  exit 1
fi

if [[ "$RESPONSE_FORMAT" == "b64_json" ]]; then
  # Determine if response has multiple images
  DATA_LEN=$(echo "$RESPONSE" | jq '(.data // []) | length')
  if [[ "$DATA_LEN" -lt 1 ]]; then
    echo "Error: image generation API response did not contain any data." >&2
    echo "$RESPONSE" >&2
    exit 1
  fi
  
  for i in $(seq 0 $((DATA_LEN - 1))); do
    # Extract base64 string
    B64=$(echo "$RESPONSE" | jq -r ".data[$i].b64_json // empty")
    if [[ -z "$B64" ]]; then
      echo "Error: image generation API response data[$i] did not include b64_json." >&2
      echo "$RESPONSE" >&2
      exit 1
    fi
    
    # Determine output file
    if [[ $DATA_LEN -gt 1 ]]; then
      OUT_FILE="${OUTPUT%.png}_${i}.png"
    else
      OUT_FILE="$OUTPUT"
    fi
    ensure_output_outside_skill "$OUT_FILE"
    
    # Decode and save
    echo "$B64" | base64 -d > "$OUT_FILE"
    echo "Saved: $OUT_FILE" >&2
  done
elif [[ "$RESPONSE_FORMAT" == "url" ]]; then
  # Download from URL
  URL=$(echo "$RESPONSE" | jq -r '.data[0].url')
  ensure_output_outside_skill "$OUTPUT"
  curl -s -o "$OUTPUT" "$URL"
  echo "Saved: $OUTPUT" >&2
else
  echo "Error: Unknown response_format '$RESPONSE_FORMAT'." >&2
  exit 1
fi
