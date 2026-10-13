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
p.MODELS["br_check"] = "groq:qwen/qwen3.8-27b"   # different family from writer
p.FALLBACK_MODELS["br_pick"] = "groq:qwen/qwen3.8-27b"
p.FALLBACK_MODELS["br_script"] = "groq:qwen/qwen3.8-27b"
p.FALLBACK_MODELS["br_check"] = "groq:openai/gpt-oss-120b"

STATE = ROOT / "data" / "state" / "brainrot_covered.json"

# Fixed persona lines — injected verbatim so the wording can never drift.
INTRO = "Hey guys, it's Trevor, back with your daily AI and tech briefing."
CTA = "Wanna hear more tech news? Like and subscribe to The Compute Club."


def _ordinal(n):
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def date_phrase(published):
    """True-by-construction relative phrase for the story date; '' if unknown."""
    if not published:
        return ""
    try:
        pub = datetime.date.fromisoformat(published[:10])
    except ValueError:
        return ""
    days = (datetime.date.today() - pub).days
    if days < 0:
        return ""
    if days == 0:
        return "earlier today"
    if days == 1:
        return "just yesterday"
    if days <= 4:
        return "a few days ago"
    if days <= 10:
        return "last week"
    if days <= 180:
        return f"on {_ordinal(pub.day)} {pub.strftime('%B')}"
    return ""


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

    when = date_phrase((src or {}).get("published", "")) if mode == "news" else ""
    print(f"   when={when!r}")

    print("== writing script")
    source_json = json.dumps(src or {"mode": "evergreen"}, indent=1)
    base_prompt = p.fill(
        "brainrot_script",
        MODE=mode,
        TOPIC=str(pick.get("topic", "")),
        ANGLE=str(pick.get("angle", "")),
        WHEN=when,
        SOURCE_JSON=source_json)

    corrections = ""
    for round_no in range(3):
        prompt = base_prompt + corrections
        for attempt in range(3):
            meta = p.json_step("br_script", prompt)
            hook = sanitize(str(meta.get("hook", "")))
            body = sanitize(str(meta.get("body", "")))
            kicker = sanitize(str(meta.get("kicker", "")))
            script = " ".join(x for x in [hook, INTRO, body, CTA, kicker] if x)
            n_words = len(script.split())
            problem = None
            if not hook or not body:
                problem = f"reply missing hook/body keys: {sorted(meta)}"
            elif when and when.lower() not in body.lower():
                problem = f"body is missing the required date phrase {when!r}"
            elif not 90 <= n_words <= 175:
                problem = f"assembled script is {n_words} words (need 90-175)"
            if problem is None:
                break
            print(f"   retry {attempt + 1}: {problem}")
        else:
            raise RuntimeError(f"script kept failing checks: {problem}")
        print(f"   {n_words} words: {hook[:70]}...")

        if mode != "news":
            break  # evergreen has no source to check against
        print("== factcheck")
        check = p.json_step("br_check", p.fill(
            "brainrot_check", SOURCE_JSON=source_json, WHEN=when,
            HOOK=hook, BODY=body, KICKER=kicker))
        if check.get("ok"):
            print("   ok")
            break
        problems = [str(x) for x in check.get("problems", [])][:6]
        for pr in problems:
            print(f"   flagged: {pr[:110]}")
        corrections = ("\n\n## Corrections required\nA factchecker rejected "
                       "the previous draft for these reasons — fix every one "
                       "while keeping the same structure and humour:\n- "
                       + "\n- ".join(problems))
    else:
        raise RuntimeError("factcheck kept rejecting the script")

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
