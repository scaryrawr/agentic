#!/usr/bin/env bash
# crop_frames.sh — Crop overlays (meeting filmstrip, taskbar) off frames.
#
# Screen recordings shared in a call often carry a participant filmstrip down
# the right edge and an OS taskbar along the bottom. Cropping a fixed region
# yields clean, doc-ready screenshots. Works on one file or a whole directory.
#
# Usage:
#   # whole directory, drop right 240px + bottom 40px from 1920x1080 frames:
#   scripts/crop_frames.sh --frames-dir /abs/selected --output-dir /abs/cropped \
#     --crop 1680x1040+0+0
#
#   # single file:
#   scripts/crop_frames.sh --input /abs/shot.png --output /abs/shot_cropped.png \
#     --crop 1650x1035+0+0
#
# Options:
#   --frames-dir DIR   Directory of images to crop (batch mode)
#   --output-dir DIR   Output directory (batch mode)
#   --input FILE       Single image to crop
#   --output FILE      Single output path
#   --crop GEOMETRY    ImageMagick crop geometry WxH+X+Y (required)
#   --help             Show this help
#
# Tip: extract the source frame at full resolution before cropping with
# scripts/extract_frame.sh for maximum sharpness.
#
# Dependencies: ImageMagick (magick or convert), python3
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SKILL_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd -P)

realpath_no_create() {
  python3 - "$1" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

FRAMES="" OUTDIR="" INPUT="" OUTPUT="" CROP=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --frames-dir) FRAMES="$2"; shift 2;;
    --output-dir) OUTDIR="$2"; shift 2;;
    --input) INPUT="$2"; shift 2;;
    --output) OUTPUT="$2"; shift 2;;
    --crop) CROP="$2"; shift 2;;
    --help) sed -n '2,27p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -n "$CROP" ]] || { echo "error: --crop GEOMETRY required (e.g. 1680x1040+0+0)" >&2; exit 2; }

resolve_output_dir() {
  local dir="$1" flag="$2"
  [[ "$dir" = /* ]] || { echo "error: $flag must be an absolute path" >&2; exit 2; }
  dir=$(realpath_no_create "$dir")
  case "$dir/" in "$SKILL_ROOT"/*) echo "error: $flag must be outside the skill" >&2; exit 2;; esac
  mkdir -p "$dir"
  printf '%s\n' "$dir"
}

resolve_output_file() {
  local file="$1" flag="$2" dir
  [[ "$file" = /* ]] || { echo "error: $flag must be an absolute path" >&2; exit 2; }
  file=$(realpath_no_create "$file")
  case "$file" in "$SKILL_ROOT"|"$SKILL_ROOT"/*) echo "error: $flag must be outside the skill" >&2; exit 2;; esac
  dir=$(dirname -- "$file")
  mkdir -p "$dir"
  printf '%s\n' "$file"
}

MAGICK="convert"; command -v magick >/dev/null 2>&1 && MAGICK="magick"

if [[ -n "$INPUT" ]]; then
  [[ -f "$INPUT" ]] || { echo "error: --input not found" >&2; exit 2; }
  [[ -n "$OUTPUT" ]] || { echo "error: --output required with --input" >&2; exit 2; }
  OUTPUT=$(resolve_output_file "$OUTPUT" "--output")
  $MAGICK "$INPUT" -crop "$CROP" +repage "$OUTPUT"
  echo "$OUTPUT" >&2
  exit 0
fi

[[ -n "$FRAMES" && -d "$FRAMES" ]] || { echo "error: --frames-dir or --input required" >&2; exit 2; }
[[ -n "$OUTDIR" ]] || { echo "error: --output-dir required in batch mode" >&2; exit 2; }
OUTDIR=$(resolve_output_dir "$OUTDIR" "--output-dir")
shopt -s nullglob nocaseglob
n=0
for f in "$FRAMES"/*.png "$FRAMES"/*.jpg "$FRAMES"/*.jpeg; do
  $MAGICK "$f" -crop "$CROP" +repage "$OUTDIR/$(basename "$f")"
  n=$((n+1))
done
echo "cropped $n images -> $OUTDIR" >&2
