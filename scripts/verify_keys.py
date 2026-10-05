"""Verify every API key in .env works and the planned models are available.

Prints only results — never the keys. Stdlib only; runs on host Python 3.14.
Usage (from the project root):  python3 scripts/verify_keys.py
"""
import json
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

GEMINI_KEYS = [
    "GEMINI_API_KEY_TOPIC",
    "GEMINI_API_KEY_SCRIPT_CHECK",
    "GEMINI_API_KEY_CODE",
    "GEMINI_API_KEY_REPAIR",
    "GEMINI_API_KEY_METADATA",
]
# Models the handover plans to use (Section 2.2)
WANTED_MODELS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.1-pro-preview"]


def load_env():
    env = {}
    for line in ENV_PATH.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, _, value = line.partition("=")
            env[name.strip()] = value.strip()
    return env


def get_json(url, headers=None, body=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "shorts-pipeline/0.1",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def check_gemini(name, key):
    if not key:
        print(f"{name}: MISSING (empty in .env)")
        return
    try:
        data = get_json(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
            headers={"x-goog-api-key": key},
        )
    except urllib.error.HTTPError as e:
        print(f"{name}: FAILED (HTTP {e.code}: {e.reason})")
        return
    except Exception as e:
        print(f"{name}: FAILED ({type(e).__name__})")
        return
    available = {m["name"].removeprefix("models/") for m in data.get("models", [])}
    found = [m for m in WANTED_MODELS if m in available]
    missing = [m for m in WANTED_MODELS if m not in available]
    print(f"{name}: OK — has {found}" + (f", missing {missing}" if missing else ""))


def check_hf(key):
    if not key:
        print("HF_TOKEN: MISSING (empty in .env)")
        return
    try:
        data = get_json(
            "https://router.huggingface.co/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            body={
                "model": "meta-llama/Llama-3.3-70B-Instruct",
                "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                "max_tokens": 5,
            },
        )
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = " — " + e.read().decode()[:200]
        except Exception:
            pass
        print(f"HF_TOKEN: FAILED (HTTP {e.code}: {e.reason}){detail}")
        return
    except Exception as e:
        print(f"HF_TOKEN: FAILED ({type(e).__name__})")
        return
    reply = data["choices"][0]["message"]["content"].strip()
    print(f"HF_TOKEN: OK — Llama-3.3-70B replied: {reply!r}")


if __name__ == "__main__":
    env = load_env()
    for name in GEMINI_KEYS:
        check_gemini(name, env.get(name, ""))
    check_hf(env.get("HF_TOKEN", ""))
