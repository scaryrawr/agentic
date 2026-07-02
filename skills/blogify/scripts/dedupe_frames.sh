#!/usr/bin/env bash
# dedupe_frames.sh — Drop near-identical consecutive frames before classifying.
#
# Scene sampling produces many almost-identical frames (mouse moves, scrolls).
# Deduping first cuts the number of (slower) vision calls the classifier makes.
# Uses ImageMagick's normalized RMSE between consecutive frames.
#
# Usage:
#   scripts/dedupe_frames.sh --frames-dir /abs/frames --output-dir /abs/frames_dedup
#
# Options:
#   --frames-dir DIR   Directory of sampled frames (required)
#   --output-dir DIR   Where to copy the kept frames (required)
#   --threshold N      RMSE distance 0-1; higher keeps fewer (default: 0.06)
#   --help             Show this help
#
# Dependencies: ImageMagick (magick or compare), python3
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SKILL_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd -P)

realpath_no_create() {
  python3 - "$1" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

FRAMES="" OUTDIR="" THRESH=0.06
while [[ $# -gt 0 ]]; do
  case "$1" in
    --frames-dir) FRAMES="$2"; shift 2;;
    --output-dir) OUTDIR="$2"; shift 2;;
    --threshold) THRESH="$2"; shift 2;;
    --help) sed -n '2,17p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
[[ -n "$FRAMES" && -d "$FRAMES" ]] || { echo "error: --frames-dir required" >&2; exit 2; }
[[ -n "$OUTDIR" ]] || { echo "error: --output-dir required" >&2; exit 2; }
[[ "$OUTDIR" = /* ]] || { echo "error: --output-dir must be an absolute path" >&2; exit 2; }
[[ "$THRESH" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || { echo "error: --threshold must be a number between 0 and 1" >&2; exit 2; }
python3 - "$THRESH" <<'PY' || { echo "error: --threshold must be a number between 0 and 1" >&2; exit 2; }
import sys
threshold = float(sys.argv[1])
sys.exit(0 if 0 <= threshold <= 1 else 1)
PY
FRAMES=$(cd -- "$FRAMES" && pwd -P)
OUTDIR=$(realpath_no_create "$OUTDIR")
case "$OUTDIR/" in "$SKILL_ROOT"/*) echo "error: --output-dir must be outside the skill" >&2; exit 2;; esac
[[ "$OUTDIR" != "$FRAMES" ]] || { echo "error: --output-dir must differ from --frames-dir" >&2; exit 2; }
mkdir -p "$OUTDIR"
find "$OUTDIR" -maxdepth 1 -type f -name '*.jpg' -exec rm -f {} +

CMP="compare"; command -v magick >/dev/null 2>&1 && CMP="magick compare"

prev=""; kept=0; total=0
while IFS= read -r f; do
  total=$((total+1))
  if [[ -z "$prev" ]]; then cp "$f" "$OUTDIR/"; prev="$f"; kept=$((kept+1)); continue; fi
  rmse=$($CMP -metric RMSE "$prev" "$f" null: 2>&1 || true)
  rmse=$(printf '%s\n' "$rmse" | sed -E 's/.*\(([0-9.]+)\).*/\1/')
  keep=$(python3 - "${rmse:-1}" "$THRESH" <<'PY' 2>/dev/null || echo 1
import sys
rmse, threshold = map(float, sys.argv[1:3])
print(1 if rmse > threshold else 0)
PY
)
  if [[ "$keep" == "1" ]]; then cp "$f" "$OUTDIR/"; prev="$f"; kept=$((kept+1)); fi
done < <(find "$FRAMES" -maxdepth 1 -type f -name '*.jpg' | sort)
echo "kept $kept of $total -> $OUTDIR" >&2
