#!/bin/bash
# Fill the cloud queue to 5 by dispatching topup runs on GitHub's machines.
# Local footprint: this loop only sleeps and polls.
R="AadityaKaushik/shorts-pipeline"
for cycle in 1 2 3 4; do
    count=$(gh -R "$R" release list --limit 100 --json tagName --jq '.[].tagName' | grep -c '^queue-')
    echo "cycle $cycle: cloud queue at $count"
    if [ "$count" -ge 5 ]; then
        echo "QUEUE_FULL"
        exit 0
    fi
    gh -R "$R" workflow run topup.yml
    sleep 20
    run_id=$(gh -R "$R" run list --workflow topup.yml --limit 1 --json databaseId --jq '.[0].databaseId')
    echo "watching run $run_id"
    gh -R "$R" run watch "$run_id" --exit-status > /dev/null 2>&1 \
        && echo "run $run_id: success" || echo "run $run_id: FAILED"
done
count=$(gh -R "$R" release list --limit 100 --json tagName --jq '.[].tagName' | grep -c '^queue-')
echo "final cloud queue: $count"
[ "$count" -ge 5 ]
