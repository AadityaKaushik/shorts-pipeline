#!/bin/bash
# Launch morning: wait for the scheduled daily run to appear, watch it finish,
# then report its conclusion and the state of the cloud queue.
cd "$(dirname "$0")/.."
echo "waiting for the scheduled 'daily' run to appear..."
run_id=""
for i in $(seq 1 120); do
    run_id=$(gh run list --workflow daily.yml --event schedule --limit 1 \
             --json databaseId,createdAt \
             --jq '.[0].databaseId // empty' 2>/dev/null)
    if [ -n "$run_id" ]; then
        echo "scheduled run appeared: $run_id"
        break
    fi
    sleep 30
done
if [ -z "$run_id" ]; then
    echo "NO_SCHEDULED_RUN after 60 minutes"
    exit 1
fi
gh run watch "$run_id" --exit-status > /dev/null 2>&1
status=$?
echo "=== run finished, exit=$status"
gh run view "$run_id" --json conclusion,jobs \
    --jq '.conclusion, (.jobs[] | .name + ": " + .conclusion)'
echo "=== cloud queue now:"
gh release list --limit 100 --json tagName --jq '.[].tagName' | grep '^queue-' | sort
echo "=== publish log (last entry):"
git pull -q --rebase 2>/dev/null
tail -c 600 data/state/publish_log.json 2>/dev/null || echo "(no publish log yet)"
exit $status
