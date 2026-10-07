"""Exercise the Phase 5 renderer endpoints: validate, prompt, queue, history, package."""
import json
import urllib.request
from pathlib import Path

BASE = "http://localhost:8000"
ROOT = Path(__file__).resolve().parent.parent


def call(method, path, body=None):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


# 1. /validate: good code passes, bad code fails with reasons
good = (ROOT / "examples" / "ex1_eigenvectors.py").read_text(encoding="utf-8")
n = len(json.loads((ROOT / "examples" / "ex1_eigenvectors.json")
                   .read_text(encoding="utf-8"))["segments"])
r = call("POST", "/validate", {"code": good, "segments_count": n})
print("validate(good):", r)
assert r["ok"], "good example should pass"

bad = "import os\nclass Main:\n    pass\n"
r = call("POST", "/validate", {"code": bad, "segments_count": 3})
print("validate(bad):", r["ok"], "|", len(r["errors"]), "errors")
assert not r["ok"]

# 2. /prompt/topic fills vars; /prompt/code injects examples
r = call("POST", "/prompt/topic", {"vars": {"HISTORY": "- t1 (math)",
                                            "RECENT_CATEGORIES": "math, physics"}})
assert r["ok"] and "- t1 (math)" in r["prompt"] and "{{" not in r["prompt"]
print("prompt/topic: OK, filled")
r = call("POST", "/prompt/code", {"vars": {"SEGMENTS_JSON": "[]"}})
assert r["ok"] and "### Example 3" in r["prompt"]
print("prompt/code: OK, examples injected")

# 3. queue + history
print("queue/status:", call("GET", "/queue/status"))
h = call("GET", "/history")
print("history:", len(h["topics"]), "topics | recent:", h["recent_categories"])

# 4. /package with the existing gauss render, then show the result
r = call("POST", "/package", {
    "job_id": "gauss",
    "topic": {"topic": "PACKAGE TEST delete me", "category": "test"},
    "script": {"segments": []},
    "metadata": {"title": "test"},
    "attempts": [{"note": "endpoint test"}],
})
print("package:", r)
assert r["ok"]
print("queue after:", call("GET", "/queue/status"))
