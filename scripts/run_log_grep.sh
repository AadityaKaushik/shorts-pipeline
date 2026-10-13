#!/usr/bin/env bash
# Usage: bash scripts/run_log_grep.sh RUN_ID PATTERN — matching lines of a run's full log.
cd "$(dirname "$0")/.."
gh run view "$1" --log | cut -f3- | sed 's/^[0-9TZ:.-]* //' | grep -E "$2"
