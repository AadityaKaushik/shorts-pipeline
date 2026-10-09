import ast, base64, hashlib, json, os, re, shutil, subprocess, urllib.request, uuid
from datetime import date
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path("/files/renders")
QUEUE = Path("/files/queue")
STATE = Path("/files/state")
PROMPTS = Path("/prompts")      # mounted read-only from ./prompts
EXAMPLES = Path("/examples")    # mounted read-only from ./examples
TIMEOUT = int(os.getenv("RENDER_TIMEOUT", "900"))
DEFAULT_VOICE = os.getenv("TTS_VOICE", "af_heart")
TTS_URL = os.getenv("TTS_URL", "http://tts:8001")
BOX_CHARS = re.compile(r"[\u2500-\u257f\u2771]")

app = FastAPI()


OUTRO_FILE = Path(os.getenv("OUTRO_FILE", "/assets/outro.mp4"))
BGM_FILE = Path(os.getenv("BGM_FILE", ""))
BGM_VOLUME = float(os.getenv("BGM_VOLUME", "0.09"))


class Job(BaseModel):
    code: str
    scene: str = "Main"
    job_id: Optional[str] = None
    segments: List[str] = []
    voice: Optional[str] = None
    post: bool = True   # append outro + mix bgm; the outro itself renders with False


class PostJob(BaseModel):
    job_id: str


class ValidateJob(BaseModel):
    code: str
    segments_count: int


class PromptFill(BaseModel):
    vars: dict = {}


class PackageJob(BaseModel):
    job_id: str
    topic: dict
    script: dict
    metadata: dict
    attempts: list = []


def clean_error(text, limit=4000):
    lines = []
    for line in BOX_CHARS.sub("", text).splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)[-limit:]


def synth(text, voice):
    body = json.dumps({"text": text, "voice": voice}).encode()
    req = urllib.request.Request(f"{TTS_URL}/speak", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read())
    return base64.b64decode(data["audio_b64"]), data["duration"], data.get("words", [])


def build_narration(d, segments, voice):
    adir = d / "audio"
    adir.mkdir(exist_ok=True)
    out = []
    for text in segments:
        key = hashlib.md5(f"{voice}|{text}".encode()).hexdigest()[:12]
        wav = adir / f"{key}.wav"
        meta_path = adir / f"{key}.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        if not (wav.exists() and "words" in meta):
            audio, dur, words = synth(text, voice)
            wav.write_bytes(audio)
            meta = {"duration": dur, "words": words}
            meta_path.write_text(json.dumps(meta))
        out.append({"text": text, "audio": str(wav),
                    "duration": round(meta["duration"], 3), "words": meta["words"]})
    (d / "narration.json").write_text(json.dumps({"voice": voice, "segments": out}, indent=2))
    return out


def video_duration(path):
    try:
        import av
        with av.open(str(path)) as c:
            return round(c.duration / 1_000_000, 2)
    except Exception:
        return None


def post_process(d: Path):
    """Append the channel outro, then mix background music under the whole
    thing (subtle: BGM_VOLUME, fade in, fade out at the end). Replaces
    final.mp4 in place. Returns None on success or an error string."""
    final = d / "final.mp4"
    if not OUTRO_FILE.exists():
        return None  # no assets configured: leave the video as rendered
    # Keep the raw render so post-processing is repeatable (e.g. volume tweaks):
    # first run saves it, later runs start over from it.
    raw = d / "final_raw.mp4"
    if raw.exists():
        shutil.copy2(raw, final)
    else:
        shutil.copy2(final, raw)
    tmp_concat = d / "tmp_concat.mp4"
    tmp_mix = d / "tmp_mix.mp4"

    def run(cmd):
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if p.returncode != 0:
            return (p.stderr or p.stdout)[-1500:]
        return None

    err = run([
        "ffmpeg", "-y", "-i", str(final), "-i", str(OUTRO_FILE),
        "-filter_complex",
        "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0];"
        "[1:a]aformat=sample_rates=44100:channel_layouts=stereo[a1];"
        "[0:v][a0][1:v][a1]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-r", "30", str(tmp_concat),
    ])
    if err:
        return f"outro concat failed: {err}"

    if BGM_FILE and BGM_FILE.exists():
        total = video_duration(tmp_concat) or 0
        fade_start = max(total - 2.5, 0)
        err = run([
            "ffmpeg", "-y", "-i", str(tmp_concat),
            "-stream_loop", "-1", "-i", str(BGM_FILE),
            "-filter_complex",
            f"[1:a]atrim=0:{total:.2f},aformat=sample_rates=44100:channel_layouts=stereo,"
            f"volume={BGM_VOLUME},afade=t=in:d=1.5,"
            f"afade=t=out:st={fade_start:.2f}:d=2.5[m];"
            "[0:a]aformat=sample_rates=44100:channel_layouts=stereo[a0];"
            "[a0][m]amix=inputs=2:duration=first:normalize=0[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", str(tmp_mix),
        ])
        if err:
            tmp_concat.unlink(missing_ok=True)
            return f"bgm mix failed: {err}"
        shutil.move(str(tmp_mix), final)
        tmp_concat.unlink(missing_ok=True)
    else:
        shutil.move(str(tmp_concat), final)
    return None


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/postprocess")
def postprocess(job: PostJob):
    """Apply outro + bgm to an already-rendered job's final.mp4."""
    d = ROOT / job.job_id
    if not (d / "final.mp4").exists():
        return {"ok": False, "error": f"no final.mp4 in renders/{job.job_id}"}
    err = post_process(d)
    if err:
        return {"ok": False, "job_id": job.job_id, "error": err}
    return {"ok": True, "job_id": job.job_id,
            "duration": video_duration(d / "final.mp4")}


# ---------------- Phase 5 endpoints: n8n orchestrates, logic lives here ------

ALLOWED_IMPORTS = {"shorts_base", "numpy", "math"}
BANNED = re.compile(r"\bopen\s*\(|\bexec\s*\(|\beval\s*\(|__import__|subprocess|\bos\s*\.")


def static_check(code, n_segments):
    """The cheap pre-render checks from HANDOVER 11.4."""
    errors = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]
    if not any(isinstance(n, ast.ClassDef) and n.name == "Main" for n in tree.body):
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
        errors.append(f"say() indices {sorted(say_indices)} != expected "
                      f"0..{n_segments - 1}, each once")
    m = BANNED.search(code)
    if m:
        errors.append(f"banned construct: {m.group(0)!r}")
    return errors


def examples_block():
    parts = []
    for i, py in enumerate(sorted(EXAMPLES.glob("ex*.py")), 1):
        spec = json.loads(py.with_suffix(".json").read_text(encoding="utf-8"))
        parts.append(
            f"### Example {i} — segments\n\n```json\n"
            + json.dumps(spec["segments"], indent=2)
            + f"\n```\n\n### Example {i} — scene\n\n```python\n"
            + py.read_text(encoding="utf-8") + "```\n")
    return "\n".join(parts)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


@app.post("/validate")
def validate(job: ValidateJob):
    errors = static_check(job.code, job.segments_count)
    return {"ok": not errors, "errors": errors}


@app.post("/prompt/{name}")
def fill_prompt(name: str, body: PromptFill):
    """Return the prompt template with {{VARS}} filled. The code/repair prompts
    get {{EXAMPLES}} injected automatically, so n8n never assembles text."""
    if not re.fullmatch(r"[a-z_]+", name) or not (PROMPTS / f"{name}.md").exists():
        return {"ok": False, "error": f"unknown prompt {name!r}"}
    text = (PROMPTS / f"{name}.md").read_text(encoding="utf-8")
    vars_ = dict(body.vars)
    if "{{EXAMPLES}}" in text and "EXAMPLES" not in vars_:
        vars_["EXAMPLES"] = examples_block()
    for k, v in vars_.items():
        text = text.replace("{{" + k + "}}",
                            v if isinstance(v, str) else json.dumps(v, indent=2))
    return {"ok": True, "prompt": text}


@app.get("/queue/status")
def queue_status():
    QUEUE.mkdir(parents=True, exist_ok=True)
    folders = sorted(p.name for p in QUEUE.iterdir() if p.is_dir())
    return {"count": len(folders), "folders": folders}


@app.get("/history")
def history():
    f = STATE / "history.json"
    data = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"topics": []}
    recent = [t.get("category") for t in data["topics"][-2:]] or ["none yet"]
    listing = "\n".join(f"- {t['topic']} ({t.get('category')})"
                        for t in data["topics"]) or "(none yet)"
    return {"topics": data["topics"], "history_text": listing,
            "recent_categories": ", ".join(recent)}


@app.post("/package")
def package(job: PackageJob):
    src = ROOT / job.job_id
    video = src / "final.mp4"
    if not video.exists():
        return {"ok": False, "error": f"no final.mp4 in renders/{job.job_id}"}
    folder = QUEUE / f"{date.today().isoformat()}_{slugify(job.topic.get('topic', job.job_id))}"
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video, folder / "video.mp4")
    (folder / "metadata.json").write_text(json.dumps(job.metadata, indent=2),
                                          encoding="utf-8")
    (folder / "topic.json").write_text(json.dumps(job.topic, indent=2),
                                       encoding="utf-8")
    (folder / "script.json").write_text(json.dumps(job.script, indent=2),
                                        encoding="utf-8")
    scene = src / "scene.py"
    if scene.exists():
        shutil.copy2(scene, folder / "scene.py")
    (folder / "render.log").write_text(json.dumps(job.attempts, indent=2),
                                       encoding="utf-8")
    STATE.mkdir(parents=True, exist_ok=True)
    hfile = STATE / "history.json"
    data = json.loads(hfile.read_text(encoding="utf-8")) if hfile.exists() else {"topics": []}
    data["topics"].append({"topic": job.topic.get("topic"),
                           "category": job.topic.get("category"),
                           "date": date.today().isoformat()})
    hfile.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "folder": str(folder)}


@app.post("/render")
def render(job: Job):
    jid = job.job_id or uuid.uuid4().hex[:12]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", jid) or not job.scene.isidentifier():
        return {"ok": False, "job_id": jid, "stage": "input",
                "error": "invalid job_id or scene name"}

    d = ROOT / jid
    d.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(d / "media", ignore_errors=True)
    (d / "final.mp4").unlink(missing_ok=True)
    (d / "bounds_violations.json").unlink(missing_ok=True)
    (d / "scene.py").write_text(job.code, encoding="utf-8")

    try:
        narration = build_narration(d, job.segments, job.voice or DEFAULT_VOICE)
    except Exception as e:
        return {"ok": False, "job_id": jid, "stage": "tts", "error": str(e)[-2000:]}

    cmd = [
        "manim", "render", "scene.py", job.scene,
        "-r", "1080,1920", "--fps", "30",
        "--media_dir", str(d / "media"),
        "-o", "final", "--disable_caching",
    ]
    env = {**os.environ, "PYTHONPATH": "/app"}
    try:
        p = subprocess.run(cmd, cwd=d, env=env, capture_output=True,
                           text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return {"ok": False, "job_id": jid, "stage": "render",
                "error": f"render timed out after {TIMEOUT}s"}

    out = next((d / "media").rglob("final.mp4"), None)
    if p.returncode != 0 or out is None:
        return {"ok": False, "job_id": jid, "stage": "render",
                "error": clean_error(p.stderr or p.stdout)}

    # The template records any mobject that left the content area. Treat that
    # as a failure so the repair loop fixes the layout.
    vfile = d / "bounds_violations.json"
    if vfile.exists():
        violations = json.loads(vfile.read_text())
        if violations:
            return {"ok": False, "job_id": jid, "stage": "render",
                    "error": "content out of frame (video rendered but unusable); "
                             "reposition or shrink these:\n"
                             + "\n".join(violations[:12])}

    final = d / "final.mp4"
    shutil.move(str(out), final)

    if job.post:
        perr = post_process(d)
        if perr:
            return {"ok": False, "job_id": jid, "stage": "post", "error": perr}

    return {
        "ok": True,
        "job_id": jid,
        "video_path": f"/files/renders/{jid}/final.mp4",
        "duration": video_duration(final),
        "narration_seconds": round(sum(s["duration"] for s in narration), 2),
    }