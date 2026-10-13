"""List social accounts connected to a bundle.social team (read-only, no keys printed).
Usage: python3 scripts/check_bundle_accounts.py [_BR]"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.verify_keys import load_env

sfx = sys.argv[1] if len(sys.argv) > 1 else ""
env = load_env()
key, team = env["BUNDLE_SOCIAL_API_KEY" + sfx], env["BUNDLE_SOCIAL_TEAM_ID" + sfx]
req = urllib.request.Request(f"https://api.bundle.social/api/v1/team/{team}",
                             headers={"x-api-key": key, "User-Agent": "shorts-pipeline/0.1"})
data = json.loads(urllib.request.urlopen(req, timeout=30).read())
accts = data.get("socialAccounts") or []
print(f"team {data.get('name')!r}: {len(accts)} connected account(s)")
for a in accts:
    print(f"  {a.get('type')}: {a.get('username') or a.get('displayName')!r}"
          f"  disconnected={a.get('disconnected', False)}")
