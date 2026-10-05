import base64, hashlib, json, os, re, shutil, subprocess, urllib.request, uuid
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

ROOT = Path("/files/renders")
TIMEOUT = int(os.getenv("RENDER_TIMEOUT", "900"))
DEFAULT_VOICE = os.getenv("TTS_VOICE", "af_heart")
TTS_URL = os.getenv("TTS_URL", "http://tts:8001")
BOX_CHARS = re.compile(r"[\u2500-\u257f\u2771]")

app = FastAPI()


class Job(BaseModel):
    code: str
    scene: str = "Main"
    job_id: Optional[str] = None
    segments: List[str] = []
    voice: Optional[str] = None


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


@app.get("/health")
def health():
    return {"ok": True}


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
    return {
        "ok": True,
        "job_id": jid,
        "video_path": f"/files/renders/{jid}/final.mp4",
        "duration": video_duration(final),
        "narration_seconds": round(sum(s["duration"] for s in narration), 2),
    }