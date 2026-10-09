"""Verify UPLOAD_POST_PROFILE matches a real profile on the Upload-Post account.
Read-only; prints profile names and linked platforms, never the API key."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.verify_keys import load_env

env = load_env()
key = env.get("UPLOAD_POST_API_KEY", "")
want = env.get("UPLOAD_POST_PROFILE", "")

for path in ["/api/uploadposts/users", "/api/uploadposts/users/list", "/api/users"]:
    req = urllib.request.Request(
        "https://api.upload-post.com" + path,
        headers={"Authorization": f"Apikey {key}",
                 "User-Agent": "shorts-pipeline/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"{path}: HTTP {e.code}")
        continue
    except Exception as e:
        print(f"{path}: {type(e).__name__}")
        continue
    profiles = data if isinstance(data, list) else (
        data.get("profiles") or data.get("users") or data.get("data") or [])
    print(f"{path}: found {len(profiles)} profile(s)")
    found = False
    for p in profiles:
        name = p.get("username") or p.get("user") or p.get("name")
        platforms = (p.get("social_accounts") or p.get("platforms")
                     or p.get("connected") or {})
        if isinstance(platforms, dict):
            platforms = [k for k, v in platforms.items() if v]
        print(f"  profile: {name!r}  linked: {platforms}")
        if name == want:
            found = True
    print(f"UPLOAD_POST_PROFILE={want!r} -> " + ("MATCH" if found else "NO MATCH"))
    break
