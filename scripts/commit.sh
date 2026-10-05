#!/bin/bash
# Commit helper: scripts/commit.sh "message"
cd "$(dirname "$0")/.."
git add -A
git -c user.name=Aaditya -c user.email=shailendra@citiesforum.org commit -q -m "$1

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git log --oneline -1
