#!/bin/bash
# One-time: post-process the convolution video and put it back in the queue.
set -e
cd "$(dirname "$0")/.."
job=002253-why-image-blur-is-a-convolution-a1
folder=2026-10-08_why-image-blur-is-a-convolution

curl -s -X POST http://localhost:8000/postprocess \
     -H 'Content-Type: application/json' \
     -d "{\"job_id\": \"$job\"}"
echo
cp "data/renders/$job/final.mp4" "data/retired-queue/$folder/video.mp4"
mv "data/retired-queue/$folder" data/queue/
rmdir data/retired-queue 2>/dev/null || true
curl -s http://localhost:8000/queue/status
