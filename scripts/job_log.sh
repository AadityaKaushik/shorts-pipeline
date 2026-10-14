#!/usr/bin/env bash
# Usage: bash scripts/job_log.sh RUN_ID JOB_NAME [LINES] — raw log of one job via the API.
cd "$(dirname "$0")/.."
REPO=AadityaKaushik/shorts-pipeline
job=$(gh api "repos/$REPO/actions/runs/$1/jobs" -q ".jobs[] | select(.name==\"$2\") | .id")
gh api "repos/$REPO/actions/jobs/$job/logs" | sed 's/^[0-9TZ:.-]* //' | grep -v 'HTTP 429' | tail -"${3:-80}"
