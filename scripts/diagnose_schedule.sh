#!/bin/bash
# Ground-truth checks for why the scheduled run never fired.
cd "$(dirname "$0")/.."
echo "=== 1. daily.yml as GitHub sees it on main (first 14 lines):"
gh api 'repos/AadityaKaushik/shorts-pipeline/contents/.github/workflows/daily.yml?ref=main' --jq .content | base64 -d | sed -n '1,14p'
echo
echo "=== 2. local YAML parses, triggers are:"
python3 - <<'EOF'
import yaml
for f in [".github/workflows/daily.yml", ".github/workflows/topup.yml"]:
    d = yaml.safe_load(open(f))
    trig = d.get("on", d.get(True))  # yaml parses bare `on:` as boolean True
    print(f, "->", trig)
EOF
echo
echo "=== 3. workflow states per GitHub API:"
gh api repos/AadityaKaushik/shorts-pipeline/actions/workflows --jq '.workflows[] | [.name, .state, .path] | @tsv'
echo
echo "=== 4. any scheduled runs at all, ever:"
gh run list --event schedule --limit 5 || true
