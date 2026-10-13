#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
JOB=${1:-brtest}
for t in "$2" "$3" "$4"; do
  [ -z "$t" ] && continue
  docker compose exec -T renderer ffmpeg -y -v error -ss "$t" \
    -i "/files/brainrot/$JOB/final.mp4" -frames:v 1 -q:v 3 \
    "/files/brainrot/$JOB/f$t.jpg"
done
echo done
