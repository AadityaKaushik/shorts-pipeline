#!/usr/bin/env bash
# Enable GitHub Pages (built by Actions), commit site/ + pages.yml, push, and print the URL.
set -e
cd "$(dirname "$0")/.."
repo=$(gh repo view --json nameWithOwner -q .nameWithOwner)
gh api -X POST "repos/$repo/pages" -f build_type=workflow >/dev/null 2>&1 \
  || gh api -X PUT "repos/$repo/pages" -f build_type=workflow >/dev/null
git add site .github/workflows/pages.yml scripts/ship_site.sh
git commit -q -m "Add GitHub Pages site with About page and privacy policy

Needed for the YouTube API audit form (website + privacy policy URL).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git stash -q --include-untracked || true
git pull -q --rebase
git push -q
git stash pop -q 2>/dev/null || true
sleep 8
gh run list --workflow pages.yml --limit 1
gh api "repos/$repo/pages" -q .html_url
