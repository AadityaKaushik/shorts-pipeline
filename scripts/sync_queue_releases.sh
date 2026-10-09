#!/bin/bash
# Upload every local queue folder as a queue-<name> GitHub release (skip ones
# that already exist), so the cloud queue matches the local one.
set -e
cd "$(dirname "$0")/.."
existing=$(gh release list --limit 100 --json tagName -q '.[].tagName' | grep '^queue-' || true)
for dir in data/queue/*/; do
    name=$(basename "$dir")
    tag="queue-$name"
    if echo "$existing" | grep -qx "$tag"; then
        echo "exists: $tag"
        continue
    fi
    echo "uploading: $tag"
    gh release create "$tag" "$dir"* --title "queued: $name" \
        --notes "waiting to publish" --latest=false
done
echo "--- cloud queue now:"
gh release list --limit 100 --json tagName -q '.[].tagName' | grep '^queue-' | sort
