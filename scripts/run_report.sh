#!/usr/bin/env bash
# Usage: bash scripts/run_report.sh RUN_ID [--wait]
# Step outcomes + tail of the failing log. --wait polls until the run completes.
cd "$(dirname "$0")/.."
if [ "$2" = "--wait" ]; then
  until [ "$(gh run view "$1" --json status -q .status 2>/dev/null)" = "completed" ]; do
    sleep 20
  done
fi
gh run view "$1" --json conclusion -q '"conclusion: \(.conclusion)"'
gh run view "$1" --json jobs -q '.jobs[0].steps[] | "\(.conclusion)  \(.name)"'
echo "-----"
gh run view "$1" --log-failed 2>/dev/null | grep -v 'HTTP 429' | cut -f3- | sed 's/^[0-9TZ:.-]* //' | tail -30
