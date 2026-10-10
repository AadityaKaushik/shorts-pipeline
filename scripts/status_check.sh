#!/bin/bash
# One-shot production status: recent runs, cloud queue, publish history.
cd "$(dirname "$0")/.."
R="AadityaKaushik/shorts-pipeline"
date
echo "=== recent runs:"
gh -R "$R" run list --limit 6
echo "=== cloud queue:"
gh -R "$R" release list --limit 100 --json tagName --jq '.[].tagName' | grep '^queue-' | sort
echo "=== publish history:"
gh api "repos/$R/contents/data/state/publish_log.json?ref=main" --jq .content \
  | base64 -d \
  | python3 -c "
import json, sys
for p in json.load(sys.stdin)['posts']:
    print(p['date'], p['time'][11:16], p['provider'], 'ok' if p['ok'] else 'FAILED', '-', p['title'])
"
