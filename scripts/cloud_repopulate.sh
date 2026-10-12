#!/bin/bash
# Fill the cloud queue to 5 via topup runs on GitHub's machines.
# Polls run conclusions (robust to local network blips); waits out any run
# already in progress before dispatching another.
R="AadityaKaushik/shorts-pipeline"

queue_count() {
    gh -R "$R" release list --limit 100 --json tagName --jq '.[].tagName' \
        | grep -c '^queue-'
}

wait_idle() {
    for i in $(seq 1 60); do
        busy=$(gh -R "$R" run list --limit 5 \
               --json status --jq '[.[] | select(.status != "completed")] | length' \
               2>/dev/null || echo 1)
        [ "$busy" = "0" ] && return 0
        sleep 60
    done
}

for cycle in 1 2 3 4 5; do
    wait_idle
    count=$(queue_count)
    echo "cycle $cycle: cloud queue at $count"
    if [ "$count" -ge 5 ]; then
        echo "QUEUE_FULL"
        exit 0
    fi
    gh -R "$R" workflow run topup.yml
    sleep 30
    run_id=$(gh -R "$R" run list --workflow topup.yml --limit 1 \
             --json databaseId --jq '.[0].databaseId')
    echo "dispatched run $run_id"
    for i in $(seq 1 60); do
        concl=$(gh -R "$R" run view "$run_id" --json status,conclusion \
                --jq 'if .status == "completed" then .conclusion else "running" end' \
                2>/dev/null || echo running)
        if [ "$concl" != "running" ]; then
            echo "run $run_id: $concl"
            break
        fi
        sleep 60
    done
done
count=$(queue_count)
echo "final cloud queue: $count"
[ "$count" -ge 5 ]
