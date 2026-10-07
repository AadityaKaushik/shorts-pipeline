"""Phase 4 test harness: run the full generation pipeline outside n8n.

Per run: topic -> script (Llama) -> fact-check -> code (Gemini) -> static
checks -> render -> repair loop (max 3) -> metadata. Everything is saved to
data/experiments/<run_ts>/<job_id>/ plus a summary table and summary.json.

Usage (from the project root, inside Ubuntu):
    python3 pipeline_test.py --n 5
    python3 pipeline_test.py --topic "How DNS resolution works"
    python3 pipeline_test.py --n 3 --category ai_ml --code-model gemini-3.1-pro-preview
    python3 pipeline_test.py --n 20 --commit     # also append topics to history

Stdlib only. Keys come from .env and are never printed.
"""
import argparse
import ast
import http.client
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROMPTS = ROOT / "prompts"
EXAMPLES = ROOT / "examples"
HISTORY_PATH = ROOT / "data" / "state" / "history.json"
EXPERIMENTS = ROOT / "data" / "experiments"
RENDER_URL = "http://localhost:8000/render"

# Model specs are either a bare Gemini model name, or "provider:model_id" for
# an OpenAI-compatible provider from PROVIDERS. Light steps run on Groq's free
# tier (1,000 req/day) since two of the five Gemini keys are denied; code and
# repair stay on Gemini 3.8-flash (20 req/day free, enough for production).
# Free alternative for code: --code-model "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"
MODELS = {
    "topic": "groq:openai/gpt-oss-20b",
    "script": "groq:openai/gpt-oss-120b",
    "factcheck": "groq:qwen/qwen3.8-27b",   # different family from the script writer
    "code": "gemini-3.8-flash",             # --code-model overrides
    "repair": "gemini-3.8-flash",           # follows --code-model
    "metadata": "gemini-3.5-flash-lite",
}
PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "OPENROUTER_API_KEY"),
    "hf": ("https://router.huggingface.co/v1/chat/completions", "HF_TOKEN"),
}
KEY_NAMES = {
    "topic": "GEMINI_API_KEY_TOPIC",
    "factcheck": "GEMINI_API_KEY_SCRIPT_CHECK",
    "code": "GEMINI_API_KEY_CODE",
    "repair": "GEMINI_API_KEY_REPAIR",
    "metadata": "GEMINI_API_KEY_METADATA",
}

MAX_REPAIRS = 3
ALLOWED_IMPORTS = {"shorts_base", "numpy", "math"}
BANNED = re.compile(r"\bopen\s*\(|\bexec\s*\(|\beval\s*\(|__import__|subprocess|\bos\s*\.")

call_counts = {}


def load_env():
    env = {}
    for line in (ROOT / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            name, _, value = line.partition("=")
            env[name.strip()] = value.strip()
    return env


# OS environment overrides .env (handy for temporarily swapping a key)
ENV = {**load_env(),
       **{k: v for k, v in os.environ.items()
          if k.startswith("GEMINI_API_KEY_") or k == "HF_TOKEN"}}


def post_json(url, headers, body, timeout=600):
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json",
                 "User-Agent": "shorts-pipeline/0.1", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def llm_call(url, headers, body, label):
    """POST with retries/backoff on 429 and 5xx."""
    call_counts[label] = call_counts.get(label, 0) + 1
    delay = 5
    for attempt in range(7):
        try:
            return post_json(url, headers, body)
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                print(f"    [{label}] HTTP {e.code}, retrying in {delay}s")
                time.sleep(delay)
                delay = min(delay * 2, 120)
                continue
            raise
        except (TimeoutError, urllib.error.URLError, ConnectionError,
                http.client.HTTPException, json.JSONDecodeError) as e:
            print(f"    [{label}] {type(e).__name__}, retrying in {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 120)
            continue
    raise RuntimeError(f"{label}: gave up after repeated 429/5xx")


# When a model is saturated (sustained 503s/429s), these steps may fall back one
# model for the call rather than failing the run. Code/repair never fall back:
# a weaker coder would poison the success metrics.
FALLBACK_MODELS = {
    "topic": "groq:qwen/qwen3.8-27b",
    "script": "groq:openai/gpt-oss-20b",
    "factcheck": "groq:openai/gpt-oss-120b",
    "metadata": "groq:openai/gpt-oss-20b",
}


def gemini_call(step, model, prompt, want_json):
    key = ENV[KEY_NAMES[step]]
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if want_json:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    data = llm_call(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {"x-goog-api-key": key}, body, f"gemini:{model}")
    return data["candidates"][0]["content"]["parts"][0]["text"]


def chat_call(provider, model, prompt):
    url, key_name = PROVIDERS[provider]
    label = f"{provider}:{model}"
    # Free endpoints sometimes return HTTP 200 with an error payload instead of
    # "choices" — treat that as retryable, not a crash.
    body = {"model": model,
            "messages": [{"role": "user", "content": prompt}],
            # reasoning models spend output tokens thinking before the code;
            # too small a budget truncates with finish_reason "length"
            "max_tokens": 16000}
    if provider == "openrouter":
        body["reasoning"] = {"effort": "low"}
    for attempt in range(3):
        data = llm_call(
            url, {"Authorization": f"Bearer {ENV[key_name]}"}, body, label)
        if data.get("choices"):
            content = data["choices"][0].get("message", {}).get("content")
            if content and content.strip():
                return content
        err = json.dumps(data.get("error", data))[:300]
        print(f"    [{label}] response without choices: {err}; retrying in 15s")
        time.sleep(15)
    raise RuntimeError(f"{label}: no usable response after 3 tries")


def dispatch(step, spec, prompt, want_json):
    provider, _, model_id = spec.partition(":")
    if model_id and provider in PROVIDERS:
        return chat_call(provider, model_id, prompt)
    return gemini_call(step, spec, prompt, want_json)


def llm(step, prompt, model=None, want_json=True):
    spec = model or MODELS[step]
    try:
        return dispatch(step, spec, prompt, want_json)
    except RuntimeError:
        fb = FALLBACK_MODELS.get(step)
        if not fb or fb == spec:
            raise
        print(f"    [{step}] {spec} saturated, falling back to {fb}")
        return dispatch(step, fb, prompt, want_json)


def parse_json_reply(text):
    """LLM replies sometimes come fenced or with prose around the JSON."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if m:
        text = m.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in reply")
    return json.loads(text[start:end + 1])


def extract_code(text):
    m = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip() + "\n"


def fill(template_name, **tokens):
    text = (PROMPTS / f"{template_name}.md").read_text(encoding="utf-8")
    for k, v in tokens.items():
        text = text.replace("{{" + k + "}}", v)
    return text


def examples_block():
    parts = []
    for i, py in enumerate(sorted(EXAMPLES.glob("ex*.py")), 1):
        spec = json.loads(py.with_suffix(".json").read_text(encoding="utf-8"))
        parts.append(
            f"### Example {i} — segments\n\n```json\n"
            + json.dumps(spec["segments"], indent=2)
            + "\n```\n\n### Example {0} — scene\n\n```python\n".format(i)
            + py.read_text(encoding="utf-8")
            + "```\n")
    return "\n".join(parts)


# ---------------------------------------------------------------- static checks

def static_check(code, n_segments):
    errors = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]

    main = next((n for n in tree.body if isinstance(n, ast.ClassDef)
                 and n.name == "Main"), None)
    if main is None:
        errors.append("no `class Main` found")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS:
                    errors.append(f"import not allowed: {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                errors.append(f"import not allowed: from {node.module}")

    say_indices = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "say" and node.args
                and isinstance(node.args[0], ast.Constant)):
            say_indices.append(node.args[0].value)
    if sorted(say_indices) != list(range(n_segments)):
        errors.append(
            f"say() indices {sorted(say_indices)} != expected 0..{n_segments - 1}, each once")

    m = BANNED.search(code)
    if m:
        errors.append(f"banned construct: {m.group(0)!r}")
    return errors


# ---------------------------------------------------------------- pipeline steps

def step_topic(history, forced_topic, forced_category):
    if forced_topic:
        return {"category": forced_category or "unknown", "level": "university",
                "topic": forced_topic, "key_idea": "", "hook": ""}
    topics = history.get("topics", [])
    recent = [t["category"] for t in topics[-2:]] or ["none yet"]
    hist_text = "\n".join(f"- {t['topic']} ({t['category']})" for t in topics) or "(none yet)"
    prompt = fill("topic", HISTORY=hist_text, RECENT_CATEGORIES=", ".join(recent))
    if forced_category:
        prompt += f"\n\nFor this run, the category MUST be: {forced_category}\n"
    return json_step("topic", prompt)


def step_script(topic):
    prompt = fill("script", TOPIC_JSON=json.dumps(topic, indent=2))
    for attempt in range(3):
        try:
            script = parse_json_reply(llm("script", prompt))
            assert isinstance(script["segments"], list) and script["segments"]
            return script
        except (ValueError, KeyError, AssertionError, json.JSONDecodeError) as e:
            print(f"    script reply unparsable ({e}), retrying")
    raise RuntimeError("script: no valid JSON after 3 tries")


def step_factcheck(topic, script):
    prompt = fill("factcheck", TOPIC_JSON=json.dumps(topic, indent=2),
                  SCRIPT_JSON=json.dumps(script, indent=2))
    return json_step("factcheck", prompt)


def render(job_id, code, segments):
    body = {"code": code, "scene": "Main", "job_id": job_id,
            "segments": [s["narration"] for s in segments]}
    return post_json(RENDER_URL, {}, body, timeout=1800)


def step_metadata(topic, segments):
    narration = " ".join(s["narration"] for s in segments)
    prompt = fill("metadata", TOPIC_JSON=json.dumps(topic, indent=2),
                  NARRATION_TEXT=narration)
    return json_step("metadata", prompt)


def json_step(step, prompt, model=None):
    """LLM call + JSON parse with re-ask retries, for every JSON-output step."""
    for attempt in range(3):
        try:
            return parse_json_reply(llm(step, prompt, model=model))
        except ValueError as e:  # includes JSONDecodeError
            print(f"    {step} reply unparsable ({str(e)[:80]}), retrying")
    raise RuntimeError(f"{step}: no valid JSON after 3 tries")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


# ---------------------------------------------------------------- one full run

def run_one(run_dir, history, args, idx):
    t0 = time.time()
    row = {"topic": "?", "first_try": False, "attempts": 0, "ok": False,
           "duration": None, "narration_seconds": None, "wall": 0.0,
           "fail_stage": None}

    if args.reuse:
        # Replay topic + checked script from a previous experiment job dir,
        # spending zero topic/script/factcheck calls. Great for iterating on
        # the code prompt within the 20/day flash budget.
        src = Path(args.reuse)
        topic = json.loads((src / "topic.json").read_text(encoding="utf-8"))
        fc = json.loads((src / "factcheck.json").read_text(encoding="utf-8"))
        script = json.loads((src / "script.json").read_text(encoding="utf-8"))
        segments = fc.get("segments") or script["segments"]
    else:
        topic = step_topic(history, args.topic, args.category)
    row["topic"] = topic["topic"]
    job_id = f"{datetime.now():%H%M%S}-{slugify(topic['topic'])}" or f"job{idx}"
    jdir = run_dir / job_id
    jdir.mkdir(parents=True, exist_ok=True)
    save = lambda name, obj: (jdir / name).write_text(
        json.dumps(obj, indent=2), encoding="utf-8")
    save("topic.json", topic)
    print(f"  topic: {topic['topic']} [{topic.get('category')}]"
          + (" (reused)" if args.reuse else ""))

    if not args.reuse:
        # script, with regeneration if the fact-check rejects it (max 2 regens)
        segments = None
        for attempt in range(3):
            script = step_script(topic)
            save("script.json", script)
            fc = step_factcheck(topic, script)
            save("factcheck.json", fc)
            if fc.get("ok"):
                segments = fc.get("segments") or script["segments"]
                if fc.get("issues"):
                    print(f"    fact-check fixed: {len(fc['issues'])} issue(s)")
                break
            print(f"    fact-check rejected script (attempt {attempt + 1}): "
                  f"{'; '.join(fc.get('issues', []))[:200]}")
        if segments is None:
            row["fail_stage"] = "factcheck"
            row["wall"] = round(time.time() - t0, 1)
            return row

    # code -> static checks -> render -> repair loop
    code_model = args.code_model or MODELS["code"]
    seg_json = json.dumps(segments, indent=2)
    reply = llm("code", fill("code", EXAMPLES=examples_block(),
                             SEGMENTS_JSON=seg_json),
                model=code_model, want_json=False)
    code = extract_code(reply)

    result = None
    for attempt in range(1 + MAX_REPAIRS):
        row["attempts"] = attempt + 1
        (jdir / f"scene_attempt{attempt + 1}.py").write_text(code, encoding="utf-8")

        errors = static_check(code, len(segments))
        if errors:
            error_text = "static checks failed:\n" + "\n".join(errors)
            result = {"ok": False, "stage": "static", "error": error_text}
        else:
            result = render(f"{job_id}-a{attempt + 1}", code, segments)
            if not result.get("ok") and result.get("stage") == "tts":
                print("    tts failed, retrying once")
                result = render(f"{job_id}-a{attempt + 1}", code, segments)
        save(f"render_attempt{attempt + 1}.json", result)

        if result.get("ok"):
            row["first_try"] = attempt == 0
            break
        if result.get("stage") == "tts":
            row["fail_stage"] = "tts"
            row["wall"] = round(time.time() - t0, 1)
            return row
        print(f"    attempt {attempt + 1} failed ({result.get('stage')}): "
              f"{str(result.get('error'))[:150]}")
        if attempt == MAX_REPAIRS:
            break
        reply = llm("repair", fill("repair", ERROR=str(result.get("error")),
                                   CODE=code, SEGMENTS_JSON=seg_json),
                    model=code_model, want_json=False)
        code = extract_code(reply)

    if not result.get("ok"):
        row["fail_stage"] = result.get("stage", "render")
        row["wall"] = round(time.time() - t0, 1)
        return row

    row["ok"] = True
    row["duration"] = result.get("duration")
    row["narration_seconds"] = result.get("narration_seconds")
    save("result.json", {"video_path": result["video_path"], **result})

    meta = step_metadata(topic, segments)
    save("metadata.json", meta)
    print(f"    OK: {result['video_path']} ({result.get('duration')}s)")

    if args.commit:
        history.setdefault("topics", []).append(
            {"topic": topic["topic"], "category": topic.get("category"),
             "date": f"{datetime.now():%Y-%m-%d}"})
        HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")

    row["wall"] = round(time.time() - t0, 1)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=1, help="number of runs")
    ap.add_argument("--topic", help="force this topic (single run)")
    ap.add_argument("--category", help="force the category")
    ap.add_argument("--code-model", help="override the code/repair model")
    ap.add_argument("--commit", action="store_true",
                    help="append successful topics to history.json")
    ap.add_argument("--reuse", metavar="DIR",
                    help="replay topic/script/factcheck JSONs from a previous "
                         "experiment job dir; only code/repair/metadata call out")
    args = ap.parse_args()

    history = (json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
               if HISTORY_PATH.exists() else {"topics": []})
    run_ts = f"{datetime.now():%Y%m%d_%H%M%S}"
    run_dir = EXPERIMENTS / run_ts
    run_dir.mkdir(parents=True, exist_ok=True)
    print(f"run: {run_dir}")

    rows = []
    n = 1 if args.topic else args.n
    for i in range(n):
        print(f"[{i + 1}/{n}]")
        try:
            rows.append(run_one(run_dir, history, args, i))
        except Exception as e:
            print(f"    run failed: {type(e).__name__}: {str(e)[:300]}")
            rows.append({"topic": "?", "first_try": False, "attempts": 0,
                         "ok": False, "duration": None, "narration_seconds": None,
                         "wall": 0.0, "fail_stage": f"exception:{type(e).__name__}"})

    # summary
    print("\n" + "=" * 100)
    hdr = f"{'topic':<42} {'ok':<4} {'1st':<4} {'att':<4} {'dur':<6} {'narr':<6} {'wall':<7} fail"
    print(hdr)
    print("-" * 100)
    for r in rows:
        print(f"{r['topic'][:40]:<42} {str(r['ok']):<4} {str(r['first_try']):<4} "
              f"{r['attempts']:<4} {str(r['duration']):<6} "
              f"{str(r['narration_seconds']):<6} {r['wall']:<7} {r['fail_stage'] or ''}")
    ok = [r for r in rows if r["ok"]]
    summary = {
        "runs": len(rows),
        "final_success": len(ok),
        "final_success_rate": round(len(ok) / len(rows), 3) if rows else 0,
        "first_try_success": sum(1 for r in rows if r["first_try"]),
        "avg_attempts": round(sum(r["attempts"] for r in rows) / len(rows), 2) if rows else 0,
        "durations": [r["duration"] for r in ok],
        "in_65_90s": sum(1 for r in ok if r["duration"] and 65 <= r["duration"] <= 90),
        "model_calls": call_counts,
        "code_model": args.code_model or MODELS["code"],
        "rows": rows,
    }
    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2),
                                          encoding="utf-8")
    print(f"\nsuccess {len(ok)}/{len(rows)}, "
          f"first-try {summary['first_try_success']}/{len(rows)}, "
          f"calls: {call_counts}")
    print(f"summary: {run_dir / 'summary.json'}")


if __name__ == "__main__":
    main()
