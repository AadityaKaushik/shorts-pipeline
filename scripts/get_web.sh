#!/usr/bin/env bash
# Usage: bash scripts/get_web.sh RUN_ID [preview|full] — download a webvideo artifact to data/webvideo/<mode>/
cd "$(dirname "$0")/.."
mode=${2:-preview}
rm -rf "data/webvideo/$mode"
for i in 1 2 3; do
  gh run download "$1" -n "webvideo-$mode" -D "data/webvideo/$mode" && break
  sleep 5
done
ls "data/webvideo/$mode"
cat "data/webvideo/$mode/timeline.json" | tr -d '\n ' | head -c 400; echo
