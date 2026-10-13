"""Check an Upload-Post async upload: python3 scripts/upload_post_status.py REQUEST_ID [_BR]"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.verify_keys import load_env

rid, sfx = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
key = load_env()["UPLOAD_POST_API_KEY" + sfx]
req = urllib.request.Request(
    f"https://api.upload-post.com/api/uploadposts/status?request_id={rid}",
    headers={"Authorization": f"Apikey {key}", "User-Agent": "shorts-pipeline/0.1"})
print(json.dumps(json.loads(urllib.request.urlopen(req, timeout=30).read()), indent=1)[:1500])
