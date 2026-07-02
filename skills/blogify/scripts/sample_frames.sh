#!/usr/bin/env bash
# sample_frames.sh — Extract candidate frames from a video, named by timestamp.
#
# Combines scene-change detection with a periodic fallback so static slides
# (which trigger no scene change) are still captured. A LOW scene threshold is
# deliberate: a high threshold (e.g. 0.3) silently skips important content such
# as diff/terminal demos. Frames are named t_<MMmSSs>_f<frame>.jpg using the
# real presentation timestamp parsed from ffmpeg's showinfo filter.
#
# Usage:
#   scripts/sample_frames.sh --input /abs/talk.mp4 --output-dir /abs/frames
#
# Options:
#   --input FILE       Video file (required)
#   --output-dir DIR   Output directory, must be OUTSIDE the skill (required)
#   --scene N          Scene-change threshold 0-1 (default: 0.06; lower = more)
#   --every N          Also grab a frame every N seconds (default: 4; 0 = off)
#   --width N          Downscale width in px, keeps aspect (default: 1280)
#   --start N          Start second (default: 0)   -- for targeted re-sampling
#   --end N            End second (default: full)   -- of a specific window
#   --help             Show this help
#
# Dependencies: ffmpeg, ffprobe, python3
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
SKILL_ROOT=$(cd -- "${SCRIPT_DIR}/.." && pwd -P)

INPUT="" OUTDIR="" SCENE=0.06 EVERY=4 WIDTH=1280 START=0 END=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT="$2"; shift 2;;
    --output-dir) OUTDIR="$2"; shift 2;;
    --scene) SCENE="$2"; shift 2;;
    --every) EVERY="$2"; shift 2;;
    --width) WIDTH="$2"; shift 2;;
    --start) START="$2"; shift 2;;
    --end) END="$2"; shift 2;;
    --help) sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done

is_number() {
  [[ "$1" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]]
}

is_positive_int() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

in_range() {
  python3 - "$1" "$2" "$3" <<'PY'
import sys
value, low, high = map(float, sys.argv[1:4])
sys.exit(0 if low <= value <= high else 1)
PY
}

realpath_no_create() {
  python3 - "$1" <<'PY'
import os, sys
print(os.path.realpath(sys.argv[1]))
PY
}

is_nonzero() {
  python3 - "$1" <<'PY'
import sys
sys.exit(0 if float(sys.argv[1]) != 0 else 1)
PY
}

[[ -n "$INPUT" && -f "$INPUT" ]] || { echo "error: --input file required" >&2; exit 2; }
[[ -n "$OUTDIR" ]] || { echo "error: --output-dir required" >&2; exit 2; }
[[ "$OUTDIR" = /* ]] || { echo "error: --output-dir must be an absolute path" >&2; exit 2; }
is_number "$SCENE" && in_range "$SCENE" 0 1 || { echo "error: --scene must be a number between 0 and 1" >&2; exit 2; }
is_number "$EVERY" || { echo "error: --every must be a non-negative number" >&2; exit 2; }
is_positive_int "$WIDTH" || { echo "error: --width must be a positive integer" >&2; exit 2; }
is_number "$START" || { echo "error: --start must be a non-negative number" >&2; exit 2; }
[[ -z "$END" || "$END" =~ ^([0-9]+([.][0-9]*)?|[.][0-9]+)$ ]] || { echo "error: --end must be a non-negative number" >&2; exit 2; }
if [[ -n "$END" ]]; then
  python3 - "$START" "$END" <<'PY' || { echo "error: --end must be greater than --start" >&2; exit 2; }
import sys
start, end = map(float, sys.argv[1:3])
sys.exit(0 if end > start else 1)
PY
fi
OUTDIR=$(realpath_no_create "$OUTDIR")
case "$OUTDIR/" in "$SKILL_ROOT"/*) echo "error: --output-dir must be outside the skill" >&2; exit 2;; esac
mkdir -p "$OUTDIR"
find "$OUTDIR" -maxdepth 1 -type f -name 't_*m*s_f*.jpg' -exec rm -f {} +
raw="$OUTDIR/_raw"; mkdir -p "$raw"; rm -f "$raw"/*.jpg 2>/dev/null || true

# frame rate (for the periodic modulo term)
fps=$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate \
      -of default=noprint_wrappers=1:nokey=1 "$INPUT" | awk -F/ '{if($2)print $1/$2; else print $1}')
[[ -z "$fps" || "$fps" == "0" ]] && fps=25

# Build the select expression: scene change OR every N seconds.
sel="gt(scene,$SCENE)"
if is_nonzero "$EVERY"; then
  mod=$(awk -v every="$EVERY" -v fps="$fps" 'BEGIN{printf "%d", every*fps}')
  [[ "$mod" -lt 1 ]] && mod=1
  sel="$sel+not(mod(n,$mod))"
fi

trim=()
[[ "$START" != "0" ]] && trim+=(-ss "$START")
[[ -n "$END" ]] && trim+=(-to "$END")

echo "Sampling frames (scene>$SCENE, every ${EVERY}s, fps~${fps})..." >&2
ffmpeg_status=0
ffmpeg -y ${trim[@]+"${trim[@]}"} -i "$INPUT" \
  -vf "select='${sel}',showinfo,scale=${WIDTH}:-1" -vsync vfr \
  "$raw/f_%05d.jpg" 2>"$OUTDIR/showinfo.log" || ffmpeg_status=$?
if [[ "$ffmpeg_status" -ne 0 ]]; then
  if ! find "$raw" -maxdepth 1 -type f -name '*.jpg' | read -r _ && grep -Eq 'Nothing was written|Output file is empty' "$OUTDIR/showinfo.log"; then
    rm -rf "$raw"
    echo "0 frames matched -> $OUTDIR (lower --scene or enable --every)" >&2
    exit 0
  fi
  echo "error: ffmpeg failed while sampling frames; see $OUTDIR/showinfo.log" >&2
  exit "$ffmpeg_status"
fi

# Pair each output frame with its real pts_time (in showinfo order) and rename.
OFFSET="$START" python3 - "$raw" "$OUTDIR" "$OUTDIR/showinfo.log" <<'PY'
import os, re, sys
raw, outdir, log = sys.argv[1:4]
offset = float(os.environ.get("OFFSET", "0") or 0)
times = [float(m) for m in re.findall(r"pts_time:([0-9.]+)", open(log, errors="ignore").read())]
files = sorted(f for f in os.listdir(raw) if f.endswith(".jpg"))
if not files:
    os.rmdir(raw)
    print(f"0 frames matched -> {outdir} (lower --scene or enable --every)", file=sys.stderr)
    sys.exit(0)
kept = 0
for i, f in enumerate(files):
    secs = (times[i] if i < len(times) else i) + offset
    m, s = divmod(int(round(secs)), 60)
    name = f"t_{m:03d}m{s:02d}s_f{i:04d}.jpg"
    os.replace(os.path.join(raw, f), os.path.join(outdir, name))
    kept += 1
os.rmdir(raw)
print(f"{kept} frames -> {outdir}", file=sys.stderr)
PY
