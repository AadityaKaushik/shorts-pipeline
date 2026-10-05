#!/bin/bash
# One-time: clean junk file and make the initial commit.
cd "$(dirname "$0")/.."
git rm --cached -q 'docs/shorts_pipeline_handover.md:Zone.Identifier' 2>/dev/null
rm -f 'docs/shorts_pipeline_handover.md:Zone.Identifier'
grep -q 'Zone.Identifier' .gitignore || echo '*:Zone.Identifier' >> .gitignore
git add -A
git -c user.name=Aaditya -c user.email=shailendra@citiesforum.org commit -q -m "Initial commit: phases 1-3 (infra, renderer, TTS, render template)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git log --oneline
