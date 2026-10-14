#!/usr/bin/env bash
# Usage: bash scripts/ship_web.sh "commit message" [preview|full] — commit webvideo, push, dispatch, print run id.
set -e
cd "$(dirname "$0")/.."
grep -q '^webvideo/node_modules/' .gitignore || printf 'webvideo/node_modules/\nwebvideo/build/\n' >> .gitignore
git add .gitignore webvideo .github/workflows/webvideo.yml scripts/*.sh
git diff --cached --quiet || git commit -q -m "$1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git pull -q --rebase && git push -q
git log --oneline -1
gh workflow run webvideo.yml -f mode="${2:-preview}"
sleep 10
gh run list --workflow webvideo.yml --limit 1 --json databaseId -q '.[0].databaseId'
