#!/bin/bash
# Download a run's full logs as a zip via the API and show the generate step.
R="AadityaKaushik/shorts-pipeline"
id="$1"
cd "$(dirname "$0")/.."
rm -rf /tmp/runlog && mkdir -p /tmp/runlog
gh api "repos/$R/actions/runs/$id/logs" > /tmp/runlog/logs.zip
cd /tmp/runlog && unzip -o -q logs.zip
echo "=== files:"
ls
echo "=== generate step tail:"
cat *Generate*video*.txt 2>/dev/null | tail -35 || cat */*Generate*.txt 2>/dev/null | tail -35
