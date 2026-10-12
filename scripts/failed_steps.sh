#!/bin/bash
# Show failed steps and their log tail for a run id.
R="AadityaKaushik/shorts-pipeline"
id="$1"
gh -R "$R" run view "$id" --json jobs \
  --jq '.jobs[] | .name + " -> " + .conclusion + " | failed steps: " + ([.steps[] | select(.conclusion=="failure") | .name] | join(", "))'
echo "=== log tail of failures:"
gh -R "$R" run view "$id" --log-failed | tail -40
