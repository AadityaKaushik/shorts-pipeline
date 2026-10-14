#!/usr/bin/env bash
# Usage: bash scripts/http_errors.sh RUN_ID... — count LLM HTTP errors by model+code per run.
cd "$(dirname "$0")/.."
REPO=AadityaKaushik/shorts-pipeline
for r in "$@"; do
  echo "== run $r"
  for j in $(gh api "repos/$REPO/actions/runs/$r/jobs" -q '.jobs[].id'); do
    gh api "repos/$REPO/actions/jobs/$j/logs" \
      | grep -oE '\[(gemini|openrouter|groq)[^]]*\] HTTP [0-9]+|\[(code|repair)\][^,]*saturated' \
      | sort | uniq -c
  done
done
