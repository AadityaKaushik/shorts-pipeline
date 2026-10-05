"""List models available on Groq and OpenRouter (free ones only for OpenRouter)."""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.verify_keys import load_env

env = load_env()


def get(url, key):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {key}", "User-Agent": "shorts-pipeline/0.1"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


print("=== GROQ models ===")
data = get("https://api.groq.com/openai/v1/models", env["GROQ_API_KEY"])
for m in sorted(x["id"] for x in data["data"]):
    print(" ", m)

print("\n=== OPENROUTER free models (pricing = 0) ===")
data = get("https://openrouter.ai/api/v1/models", env["OPENROUTER_API_KEY"])
for m in sorted(data["data"], key=lambda x: x["id"]):
    p = m.get("pricing", {})
    if float(p.get("prompt", 1)) == 0 and float(p.get("completion", 1)) == 0:
        print(" ", m["id"], "| ctx:", m.get("context_length"))
