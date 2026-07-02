#!/usr/bin/env bash
# extract_frame.sh — Re-extract one full-resolution video frame.
#
# Usage:
#   scripts/extract_frame.sh --input /abs/talk.mp4 --second 123.4 --output /abs/shot.png
#
# Options:
#   --input FILE     Video file (required)
#   --second N       Timestamp in seconds on the original video timeline (required)
#   --output FILE    Output image path, outside the skill (required)
#   --help           Show this help
#
# Dependencies: ffmpeg, python3
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SKILL_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd -P)

realpath_no_create() {
  python3 - "$1" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

is_number() {
  [[ "$1" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]]
}

INPUT="" SECOND="" OUTPUT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2;;
    --second) SECOND="$2"; shift 2;;
    --output) OUTPUT="$2"; shift 2;;
    --help) sed -n '2,14p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

[[ -n "$INPUT" && -f "$INPUT" ]] || { echo "error: --input file required" >&2; exit 2; }
[[ -n "$SECOND" ]] || { echo "error: --second required" >&2; exit 2; }
is_number "$SECOND" || { echo "error: --second must be a non-negative number" >&2; exit 2; }
[[ -n "$OUTPUT" ]] || { echo "error: --output required" >&2; exit 2; }
[[ "$OUTPUT" = /* ]] || { echo "error: --output must be an absolute path" >&2; exit 2; }

OUTPUT=$(realpath_no_create "$OUTPUT")
case "$OUTPUT" in "$SKILL_ROOT"|"$SKILL_ROOT"/*) echo "error: --output must be outside the skill" >&2; exit 2;; esac
mkdir -p "$(dirname -- "$OUTPUT")"

ffmpeg -v error -y -ss "$SECOND" -i "$INPUT" -frames:v 1 "$OUTPUT"
[[ -s "$OUTPUT" ]] || { echo "error: no frame extracted at --second $SECOND" >&2; exit 1; }
echo "$OUTPUT" >&2
