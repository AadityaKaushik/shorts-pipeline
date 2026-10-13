"""Brainrot pipeline: news fetch -> story pick -> humor script -> rendered
video over gameplay. $0: Groq LLM calls, keyless news sources, local render.

Usage: python3 scripts/brainrot_pipeline.py [--dry]  (--dry = stop before render)
"""
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import pipeline_test as p
import news_fetch
import brainrot_render

p.MODELS["br_pick"] = "groq:openai/gpt-oss-120b"
p.MODELS["br_script"] = "groq:openai/gpt-oss-120b"
p.FALLBACK_MODELS["br_pick"] = "groq:qwen/qwen3.8-27b"
p.FALLBACK_MODELS["br_script"] = "groq:qwen/qwen3.8-27b"

STATE = ROOT / "data" / "state" / "brainrot_covered.json"


def load_covered():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return []


def save_covered(covered):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(covered[-60:], indent=2), encoding="utf-8")


def sanitize(text):
    """Script text doubles as captions and TTS input — keep it plain."""
    for a, b in [("—", ", "), ("–", ", "), ("‑", "-"),
                 ("…", ". "), ("“", ""), ("”", ""),
                 ("‘", "'"), ("’", "'")]:
        text = text.replace(a, b)
    text = re.sub("[" + re.escape("\"`()[]{}*_#@<>|~^") + "]", "", text)
    text = text.encode("ascii", "ignore").decode()  # captions + TTS are ASCII
    return re.sub(r"\s+", " ", text).strip()


def slugify(title):
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]


def run(dry=False):
    print("== fetching headlines")
    headlines = news_fetch.fetch_headlines()
    print(f"   {len(headlines)} headlines")
    covered = load_covered()

    print("== picking story")
    pick = p.json_step("br_pick", p.fill(
        "brainrot_pick",
        HEADLINES_JSON=json.dumps(headlines, indent=1),
        COVERED=json.dumps([c["topic"] for c in covered[-30:]])))
    mode = pick.get("mode", "evergreen")
    src = None
    if mode == "news":
        try:
            src = headlines[int(pick["id"])]
        except (KeyError, TypeError, ValueError, IndexError):
            mode = "evergreen"
    if src is not None and len(src.get("summary", "")) < 120 and src.get("url"):
        body = news_fetch.fetch_article(src["url"])
        if body:
            src = {**src, "summary": body}
    print(f"   mode={mode} topic={pick.get('topic', '?')!r}")

    print("== writing script")
    meta = p.json_step("br_script", p.fill(
        "brainrot_script",
        MODE=mode,
        TOPIC=str(pick.get("topic", "")),
        ANGLE=str(pick.get("angle", "")),
        SOURCE_JSON=json.dumps(src or {"mode": "evergreen"}, indent=1)))
    script = sanitize(meta["script"])
    n_words = len(script.split())
    print(f"   {n_words} words: {script[:90]}...")
    if not 45 <= n_words <= 140:
        raise RuntimeError(f"script length {n_words} words out of range")

    today = datetime.date.today().isoformat()
    job_id = f"{today}_{slugify(meta['title'])}"
    out = ROOT / "data" / "brainrot" / job_id
    out.mkdir(parents=True, exist_ok=True)
    (out / "metadata.json").write_text(json.dumps({
        "title": meta["title"], "description": meta.get("description", ""),
        "hashtags": meta.get("hashtags", []), "script": script,
        "mode": mode, "topic": pick.get("topic"),
        "source": (src or {}).get("url", ""), "date": today,
    }, indent=2), encoding="utf-8")

    if dry:
        print("== dry run, stopping before render")
        return job_id

    print("== rendering")
    r = brainrot_render.render(script, job_id)
    print(f"   {r['duration']}s, {r['words']} words, {r['chunks']} caption chunks")

    covered.append({"date": today, "topic": pick.get("topic", ""),
                    "title": (src or {}).get("title", meta["title"])})
    save_covered(covered)
    print(f"DONE {job_id}")
    return job_id


if __name__ == "__main__":
    run(dry="--dry" in sys.argv)
