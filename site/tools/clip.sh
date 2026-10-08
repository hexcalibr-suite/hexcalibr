#!/bin/sh
# Turn a raw recording (nozzle cam stream or screen recording) into a guide clip:
# img/<id>.webm + img/<id>.mp4 + img/<id>.jpg (poster), silent, 1280 px wide, 30 fps.
#
#   tools/clip.sh <source> <id> [start_s] [duration_s] [crop] [speed]
#
#   crop   ffmpeg crop W:H:X:Y in source pixels, e.g. 2796:1568:604:498 to cut the
#          camera out of a full-screen browser recording. Use "-" for no crop.
#   speed  playback speed, e.g. 0.5 for half speed (travel moves). Default 1.
#
# GRADE (env) is a light grade for the nozzle cam recorded slightly dark (no clipped
# highlights): a little contrast and sharpening. GRADE=none to skip it.
#
# Example: tools/clip.sh raw.mov F1_pins-nozzlecam_PLA_VC4 12 8 - 0.5
set -e
SRC=$1; ID=$2; START=${3:-0}; DUR=${4:-10}; CROP=${5:--}; SPEED=${6:-1}
[ -n "$SRC" ] && [ -n "$ID" ] || { sed -n 2,11p "$0"; exit 1; }
OUT="$(cd "$(dirname "$0")/.." && pwd)/img"; mkdir -p "$OUT"
GRADE=${GRADE:-eq=contrast=1.08:gamma=1.05,unsharp=5:5:0.6}
VF="setpts=PTS/$SPEED,scale=1280:-2,fps=30"
[ "$GRADE" != "none" ] && VF="$VF,$GRADE"
[ "$CROP" != "-" ] && VF="crop=$CROP,$VF"
ffmpeg -v error -y -ss "$START" -t "$DUR" -i "$SRC" -vf "$VF" -an \
  -c:v libx264 -crf 26 -preset slow -pix_fmt yuv420p -movflags +faststart "$OUT/$ID.mp4"
ffmpeg -v error -y -ss "$START" -t "$DUR" -i "$SRC" -vf "$VF" -an \
  -c:v libvpx-vp9 -crf 36 -b:v 0 -row-mt 1 "$OUT/$ID.webm"
ffmpeg -v error -y -sseof -1 -i "$OUT/$ID.mp4" -frames:v 1 -q:v 3 "$OUT/$ID.jpg"
ls -la "$OUT/$ID".*
