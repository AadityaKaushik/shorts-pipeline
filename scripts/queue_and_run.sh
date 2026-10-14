#!/usr/bin/env bash
# Usage: bash scripts/queue_and_run.sh [RUN_ID JOB_NAME [--wait]]
# Queued releases, plus progress of a run (--wait: poll until it completes first).
cd "$(dirname "$0")/.."
if [ "$3" = "--wait" ]; then
  until [ "$(gh run view "$1" --json status -q .status 2>/dev/null)" = "completed" ]; do
    sleep 30
  done
fi
echo "queued releases:"
gh release list --limit 50 --json tagName -q '.[].tagName' | grep '^queue-' | sort | sed 's/^/  /'
[ -z "$1" ] && exit 0
echo "run $1: $(gh run view "$1" --json status,conclusion -q '"\(.status) \(.conclusion)"')"
bash scripts/job_log.sh "$1" "$2" 600 2>/dev/null \
  | grep -E 'topic:|storyboard|saturated|attempt|FAILED|fact-check|vision|queue|DONE|generated|Released|release' | tail -30
