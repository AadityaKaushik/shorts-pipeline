"""Ask the bundle.social API for the account's team IDs (read-only)."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.verify_keys import load_env

key = load_env().get("BUNDLE_SOCIAL_API_KEY", "")
if not key:
    print("BUNDLE_SOCIAL_API_KEY missing from .env")
    sys.exit(1)

for path in ["/api/v1/organization", "/api/v1/team", "/api/v1/team/list"]:
    req = urllib.request.Request(
        "https://api.bundle.social" + path,
        headers={"x-api-key": key, "User-Agent": "shorts-pipeline/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        print(f"{path}: top-level keys: {list(data) if isinstance(data, dict) else type(data).__name__}")
        teams = data.get("teams") if isinstance(data, dict) else data
        if isinstance(teams, list):
            for t in teams:
                print(f"  TEAM: id={t.get('id')}  name={t.get('name')!r}")
        break
    except urllib.error.HTTPError as e:
        print(f"{path}: HTTP {e.code}")
    except Exception as e:
        print(f"{path}: {type(e).__name__}")
