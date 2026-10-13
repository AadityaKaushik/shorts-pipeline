#!/usr/bin/env bash
# Usage: bash scripts/wait_upload.sh REQUEST_ID [_BR] — poll Upload-Post until done (max ~15 min)
cd "$(dirname "$0")/.."
for i in $(seq 1 45); do
  out=$(python3 scripts/upload_post_status.py "$1" "$2")
  if ! echo "$out" | grep -q '"status": "processing"'; then
    echo "$out"
    exit 0
  fi
  sleep 20
done
echo "still processing after 15 min"
echo "$out"
