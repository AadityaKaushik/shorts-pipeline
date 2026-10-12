#!/bin/bash
# Delete every queue-* release and all local queue folders.
cd "$(dirname "$0")/.."
for t in $(gh release list --limit 100 --json tagName --jq '.[].tagName' | grep '^queue-'); do
    gh release delete "$t" --cleanup-tag -y && echo "deleted $t"
done
rm -rf data/queue/*
curl -s http://localhost:8000/queue/status
echo
