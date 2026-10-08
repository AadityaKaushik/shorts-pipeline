# STEM Shorts Pipeline: Full Project Handover

**Owner:** Aaditya (Linux user `aadit`)
**Handover date:** 5 October 2026
**Status:** Phases 1 to 3 complete. Phase 4 (prompts) is next.

This document records everything decided and built so far, with the exact steps and the current contents of every file, plus the detailed plan for the remaining phases. It is written for two readers: the owner, and Claude Code continuing the build.

---

## 0. How to use this document

**For the owner:** save this file as `~/shorts-pipeline/docs/HANDOVER.md`, then create the short `CLAUDE.md` from Section 20 in the project root. Claude Code reads `CLAUDE.md` automatically at the start of every session and will follow its pointer to this file.

**For Claude Code:**

- The **actual files on disk are the source of truth.** The owner applied several fixes as partial edits, so small differences from the versions here are possible. If a file differs from this document and the difference matters, show the owner the diff and ask before overwriting anything.
- Read Section 19 (working style) before your first reply.
- Never print, log or commit secrets. Keys live only in `.env`.

---

## 1. Project summary

A fully automated, self-hosted pipeline that publishes one original animated **STEM explainer YouTube Short per day**.

Each day:

1. An LLM picks a topic, never repeating a past one.
2. An LLM writes a ~45-second narration script, split into timed segments.
3. An LLM writes **Manim** animation code for that script.
4. A local render service voices the script (Kokoro TTS), renders the animation in sync with the voice, and burns in word-timed captions.
5. An LLM writes the title, description and hashtags.
6. Everything is packaged into a folder in a queue.
7. A separate daily workflow publishes the oldest queued video to YouTube.

**Goals, in priority order:**

1. A strong resume and portfolio project, with measurable reliability metrics (Section 18).
2. A real, consistently publishing educational channel.
3. Possible monetization later (Section 17), which is secondary.

---

## 2. Key decisions and why

### 2.1 Publishing without the YouTube API audit (for now)

- YouTube's `videos.insert` endpoint locks **every** video uploaded by an **unaudited** API project created after 28 July 2020 to **private**, regardless of volume. Google's own reference page says so. Even a single upload is locked, and locked videos cannot be appealed.
- Quota is not the issue: uploads have their own bucket of 100 `videos.insert` calls per day.
- **Interim solution:** publish through third-party publishing APIs whose own Google projects are already approved, on their free tiers:
  - **Upload-Post:** free tier, 10 uploads a month, 2 profiles.
  - **bundle.social:** free tier, 20 posts a month, 3 accounts.
  - Combined, that's **30 a month, one per day.** Days 1 to 10 of each month go through Upload-Post and days 11 to 30 through bundle.social; or route by a running monthly count if either service resets on the signup date rather than the calendar month. The 31st is skipped or done manually.
  - Paid fallback if the free tiers change: Post for Me ($10/mo), Postproxy ($17/mo), or Upload-Post Basic ($24/mo, $16 billed annually).
- **Long-term:** submit the YouTube API audit once the pipeline is live (Phase 8), then switch to n8n's native YouTube node (Phase 9).
- **Rejected options:** browser automation against YouTube Studio (breaks YouTube's terms and puts the channel at risk), and spreading work across extra accounts to stretch free tiers (can breach providers' terms).

### 2.2 Model split

| Step | Model | Why |
|---|---|---|
| Topic | Gemini Flash-Lite (`gemini-3.5-flash-lite`) | Easy task, cheap |
| Script | **Llama 3.3 70B** via Hugging Face Inference Providers | Good writer; the owner wanted it in the mix |
| Fact-check | Gemini Flash | University-level scripts need checking (Section 11) |
| Manim code | **Gemini** (`gemini-3.8-flash`, or `gemini-3.1-pro-preview` if available and Flash underperforms) | Hardest step, so it gets the strongest coder |
| Repair | Same model as code | Fixes its own render errors |
| Metadata | Gemini Flash-Lite | Easy task |

Model codes come from Google's model list as of October 2026. **Verify availability on the owner's key** before use (Section 10).

### 2.3 Rendering and audio decisions

- **Manim Community Edition** in Docker (`manimcommunity/manim:stable`, which is now **Python 3.14**).
- **Kokoro TTS** (82M parameters, open source, local, CPU) in a **separate container on Python 3.12**, because Kokoro does not support Python 3.14.
- **A custom sync helper instead of `manim-voiceover`:** the plugin has lagged behind Manim releases, and owning about 50 lines of sync code is more robust and better for the resume.
- **Captions are drawn by the template,** not by the AI-written code, using real **word timestamps** from Kokoro.
- **Visual style v1:** a dark background, equations, short text, simple diagrams, axes and plots, and short code snippets. Complexity increases only as render success rates allow.

### 2.4 Hosting

Everything runs on the owner's Windows PC (16 GB RAM, NVIDIA MX250, which goes unused because Manim's Cairo renderer and Kokoro both run on the CPU) inside Docker Desktop on WSL2 Ubuntu. **The PC must be on and awake at scheduled times.** The queue buffer (Phase 5) absorbs missed days.

### 2.5 Human-in-the-loop (recommended)

YouTube's July 2025 "inauthentic content" policy targets fully automated, low-effort AI channels. The automation stays, but light human direction is recommended: weekly topic approval and periodic review of the queue. See Section 17.

---

## 3. Content brief (updated scope)

- **Domains, rotating:** mathematics, physics, chemistry and other sciences, electrical, electronics and mechanical engineering, computer science and algorithms, **AI/ML**, IT, networking and systems, and **web development**.
- **Level:** mostly **university level** (about 85%), occasionally **high school** (about 15%). Not trivia like "Gauss's trick" (that's only the render smoke test). Good examples:
  - Math: why eigenvectors only stretch, the intuition behind the Fourier transform, the Jacobian determinant as area scaling
  - AI/ML: how attention weights are computed, why we need nonlinear activations, the bias-variance trade-off
  - CS: why hash table lookups are O(1) on average, how Dijkstra's algorithm works
  - Engineering and physics: how an RC circuit charges, how a transistor acts as a switch, why bridges use trusses
  - Web and IT: how TLS handshakes work, what the event loop does in JavaScript, how DNS resolution works
- **Format:** about 75 seconds (target 65 to 90; owner's decision, 5 Oct 2026, after finding 45s too shallow), **one core idea per Short explained with its WHY** — the mechanism, not just the statement — a hook in the first segment, accurate and precise.
- **Tone:** clear, confident, no hype or clickbait, no false claims.

---

## 4. Environment and architecture

### 4.1 Machine

- Windows PC, user `aadit`, hostname `HPPavilion`
- WSL2 with Ubuntu (default distro); Linux user `aadit`; host Python in Ubuntu is 3.14
- Docker Desktop with the WSL2 engine and Ubuntu integration enabled
- **All commands run in the Ubuntu terminal, never PowerShell.** Running Compose from PowerShell made `.env` not load.

### 4.2 Project location

```
~/shorts-pipeline     (= /home/aadit/shorts-pipeline)
Windows Explorer path: \\wsl.localhost\Ubuntu\home\aadit\shorts-pipeline
```

### 4.3 Containers (`docker-compose.yml`)

| Service | Image | Port (localhost only) | Role |
|---|---|---|---|
| `n8n` | `docker.n8n.io/n8nio/n8n:latest` | 5678 | Workflows, scheduling, API calls |
| `renderer` | built from `./renderer` (Manim, Python 3.14) | 8000 | Runs Manim code into MP4, plus TTS orchestration, captions and error cleanup |
| `tts` | built from `./tts` (Python 3.12, CPU PyTorch, Kokoro) | 8001 | Text to WAV, plus word timestamps |

Inside Docker, services reach each other by name: `http://renderer:8000`, `http://tts:8001`. All ports are bound to `127.0.0.1`. **The renderer executes arbitrary code and must never be exposed beyond localhost.**

### 4.4 Data flow

```
n8n ──(code + segments)──> renderer /render
                              │
                              ├──(each line)──> tts /speak ──> WAV + word timings
                              ├── writes narration.json
                              ├── runs: manim render scene.py Main -r 1080,1920 --fps 30
                              └── returns {ok, video_path, duration} or {ok:false, stage, error}
```

### 4.5 Folder layout

```
shorts-pipeline/
├── .env                      (secrets, never commit)
├── docker-compose.yml
├── docs/HANDOVER.md          (this file)
├── CLAUDE.md
├── test_scene.py             (Phase 2 smoke test)
├── test_render.py            (Phase 2 smoke test)
├── example_gauss.py          (Phase 3 smoke test, not a style example)
├── test_phase3.py            (Phase 3 smoke test)
├── renderer/
│   ├── Dockerfile
│   ├── app.py
│   └── shorts_base.py
├── tts/
│   ├── Dockerfile
│   └── tts_app.py
└── data/                     (bind-mounted at /files in n8n and renderer)
    ├── renders/<job_id>/     (scene.py, narration.json, audio/, final.mp4)
    ├── queue/                (finished videos waiting to publish)
    └── published/            (archive)
```

Planned additions: `data/state/` (Phase 5), `data/experiments/` (Phase 4), `prompts/` (Phase 4), `examples/` (Phase 4).

---

## 5. Status overview

| Phase | Name | Status |
|---|---|---|
| 1 | Accounts and setup | ✅ Done (a few items to verify, Section 10) |
| 2 | Infrastructure (WSL2, Docker, n8n, renderer, YouTube OAuth) | ✅ Done |
| 3 | Render template (TTS, sync, captions) | ✅ Done |
| 4 | Prompts, tested in a Python harness | 🔄 In progress (see 11.9) |
| 5 | Generation workflow — **moved from n8n to GitHub Actions** (owner's decision, 7 Oct 2026, to avoid keeping the PC on) | ✅ Built and cloud-tested; **schedules deliberately disabled** pending launch (see 12.9) |
| 6 | Publishing workflow | ✅ Built (`scripts/publish_daily.py`, dry-run tested); never posted yet |
| 7 | Alerts | Planned |
| 8 | Pre-launch: intro/outro/music, seed queue, enable schedules, go live | ⏸ **Waiting on owner (exams)** — see 12.9 |
| 9 | YouTube API audit, then native uploads | Planned |

---

## 6. Phase 1: Accounts and setup ✅

### Step 1: Dedicated Google account and channel

1. Create a new Google account just for the channel and enable 2-step verification.
2. Sign in to YouTube, then avatar → **Create a channel**.
3. YouTube Studio → Settings → Channel → Feature eligibility: verify the phone number.
4. Record the **channel ID** (Settings → Channel → Advanced settings, starts with `UC`).

### Step 2: Gemini API key

1. Google AI Studio → **Get API key → Create API key**. Any Google account works; it does not need to be the channel's account.
2. Store it in a password manager.

### Step 3: Google Cloud project (using the channel's account)

1. console.cloud.google.com → **New project** (for example `shorts-pipeline`). Record the **project number and ID**.
2. APIs & Services → Library → enable **YouTube Data API v3**.
3. **Google Auth Platform:**
   - **Branding:** app name, support email, home page `https://<github-username>.github.io`, privacy policy `https://<github-username>.github.io/privacy.html`, authorized domain `<github-username>.github.io`.
   - **Audience:** External, with the channel Gmail added as a test user, then **Publish app** to **In production**. In Testing mode, refresh tokens expire after 7 days. The app stays "unverified", which is fine for one user.
   - **Data access:** scope `https://www.googleapis.com/auth/youtube.upload`.
   - **Clients:** see Phase 2, Step 8.

### Step 4: Homepage and privacy policy (GitHub Pages)

Production status needs a homepage and a privacy policy URL.

1. Create a public GitHub repo named `<github-username>.github.io`.
2. Add `index.html`:

```html
<!doctype html>
<html><head><meta charset="utf-8"><title>Math Shorts Pipeline</title></head>
<body>
<h1>Math Shorts Pipeline</h1>
<p>A personal tool that generates animated math explainer videos and uploads
them to my own YouTube channel using the YouTube Data API.</p>
<p><a href="privacy.html">Privacy policy</a></p>
</body></html>
```

3. Add `privacy.html` (the YouTube terms, Google privacy and revocation links are expected by YouTube's developer policies, so keep them for the audit):

```html
<!doctype html>
<html><head><meta charset="utf-8"><title>Privacy Policy</title></head>
<body>
<h1>Privacy Policy</h1>
<p>Math Shorts Pipeline is a personal tool used only by its developer to upload
original videos to the developer's own YouTube channel through YouTube API Services.</p>
<p>It has no other users. It does not collect, store or share any data about
other people. The only data it handles is the developer's own OAuth token,
stored locally on the developer's computer.</p>
<p>By using this tool you agree to the
<a href="https://www.youtube.com/t/terms">YouTube Terms of Service</a>.
See also the <a href="https://policies.google.com/privacy">Google Privacy Policy</a>.</p>
<p>Access can be revoked at any time at
<a href="https://myaccount.google.com/permissions">Google Account permissions</a>.</p>
<p>Contact: your-email@example.com</p>
</body></html>
```

**To do:** the site still says "Math"; update the wording to "STEM" to match the new scope (Section 3).

### Step 5: Publishing services

1. **Upload-Post:** sign up on the free plan, create a profile, connect the YouTube channel, and record the API key and profile name.
2. **bundle.social:** sign up on the free plan, connect the same channel, and record the API key.
3. Optional check: post one throwaway vertical clip publicly through each dashboard, confirm it really appears **public** on the channel, then delete it.

### Step 6: Secrets list (password manager only)

Channel ID, Gemini API key, Cloud project number and ID, OAuth client ID and secret, Upload-Post API key and profile name, bundle.social API key, Hugging Face token (Phase 4), and the n8n encryption key.

---

## 7. Phase 2: Infrastructure ✅

### Step 1: WSL2

The owner already had Docker Desktop, and `wsl -l -v` showed only `docker-desktop` (version 2). What was done:

```powershell
wsl --update
wsl --install -d Ubuntu      # created Linux user "aadit"
wsl --set-default Ubuntu     # run in PowerShell, or wsl.exe from inside Ubuntu
```

### Step 2: Docker Desktop settings

- General: **Use the WSL 2 based engine**, and **Start Docker Desktop when you sign in**.
- Resources → WSL integration: **Ubuntu** on.
- Test in Ubuntu: `docker run hello-world`.

### Step 3: Project folder

```bash
mkdir -p ~/shorts-pipeline/renderer ~/shorts-pipeline/tts ~/shorts-pipeline/data/{renders,queue,published}
cd ~/shorts-pipeline
```

The project lives in Ubuntu's own filesystem rather than `/mnt/c`, because file access there is much faster for Docker.

### Step 4: `.env`

The format must be exactly `NAME=value`, one per line:

```
N8N_ENCRYPTION_KEY=<the key n8n is actually using>
GEMINI_API_KEY=<added in Phase 4>
HF_TOKEN=<added in Phase 4>
```

**Incident:** the variable name was accidentally replaced (`AadityaAt2006=...`), so n8n ran without a key and generated its own, stored in the `n8n_data` volume. The fix:

```bash
docker compose exec n8n cat /home/node/.n8n/config      # shows {"encryptionKey": "..."}
# put that value into .env as N8N_ENCRYPTION_KEY=...
docker compose up -d
```

**Whether this fix was completed is unconfirmed.** See Section 10.

### Step 5: `docker-compose.yml`

The current version is in Section 8.

### Step 6: Phase 2 smoke test

`test_scene.py`:

```python
from manim import *

config.frame_height = 8
config.frame_width = 4.5

class Main(Scene):
    def construct(self):
        title = Text("Pipeline test", font_size=40)
        eq = MathTex(r"e^{i\pi} + 1 = 0", font_size=56)
        VGroup(title, eq).arrange(DOWN, buff=0.8)
        self.play(Write(title))
        self.play(Write(eq))
        self.wait(1)
```

`test_render.py`:

```python
import json, time, urllib.request

code = open("test_scene.py", encoding="utf-8").read()
body = json.dumps({"code": code, "scene": "Main", "job_id": "test1"}).encode()
req = urllib.request.Request(
    "http://localhost:8000/render",
    data=body,
    headers={"Content-Type": "application/json"},
)
start = time.time()
print(urllib.request.urlopen(req, timeout=1000).read().decode())
print(f"took {time.time() - start:.1f}s")
```

Run with `python3 test_render.py`. The output goes to `data/renders/test1/final.mp4`.

### Step 7: n8n

Open `http://localhost:5678` and create the owner account.

### Step 8: OAuth client and YouTube credential

1. Cloud Console → Google Auth Platform → **Clients → Create client → Web application**, with authorized redirect URI `http://localhost:5678/rest/oauth2-credential/callback`.
2. Record the client ID and secret.
3. In n8n: Credentials → **YouTube OAuth2 API**, paste the ID and secret, **Sign in with Google** with the channel account, and click through the unverified-app warning (Advanced → Go to app). The status should be **connected**.

### Step 9: Keep it running

- Windows power settings: no sleep when plugged in, or at least awake at scheduled times.
- Containers use `restart: unless-stopped`; Docker Desktop starts at sign-in.
- n8n does **not** catch up on missed schedules. The queue buffer handles this.

---

## 8. Phase 3: Render template ✅

### 8.1 How sync and captions work

1. The script arrives as **segments**, one narration line each.
2. The renderer calls `tts /speak` for each segment and gets back a WAV file, its duration, and **word timestamps**. Results are cached per (voice, text) in `data/renders/<job>/audio/`, so repair re-renders don't re-synthesize.
3. The renderer writes `narration.json` (text, audio path, duration and words for each segment).
4. Scenes subclass `ShortScene` and wrap each segment in `with self.say(i) as d:`. The audio starts, captions show, and `d` is the duration. On exit, the template waits out the remaining audio plus a 0.25-second pad.
5. Captions are built from word timings into lines of at most 20 characters or 4 words, breaking at punctuation. **All caption objects are created up front, and inactive ones are parked off-screen.** See gotcha 9.4 for why.

### 8.2 Current files

#### `docker-compose.yml`

```yaml
services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    restart: unless-stopped
    ports:
      - "127.0.0.1:5678:5678"
    environment:
      - GENERIC_TIMEZONE=Asia/Kolkata
      - TZ=Asia/Kolkata
      - N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}
      - N8N_RESTRICT_FILE_ACCESS_TO=/files
      - N8N_DEFAULT_BINARY_DATA_MODE=filesystem
    volumes:
      - n8n_data:/home/node/.n8n
      - ./data:/files
    depends_on:
      - renderer

  renderer:
    build: ./renderer
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"
    environment:
      - RENDER_TIMEOUT=900
      - TTS_URL=http://tts:8001
      - TTS_VOICE=af_heart
    volumes:
      - ./data:/files
    depends_on:
      - tts
    deploy:
      resources:
        limits:
          cpus: "3"
          memory: 6g

  tts:
    build: ./tts
    restart: unless-stopped
    ports:
      - "127.0.0.1:8001:8001"
    environment:
      - TTS_VOICE=af_heart
    volumes:
      - tts_cache:/cache
    deploy:
      resources:
        limits:
          cpus: "2"
          memory: 3g

volumes:
  n8n_data:
  tts_cache:
```

#### `tts/Dockerfile`

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng \
    && rm -rf /var/lib/apt/lists/*

# CPU-only PyTorch keeps the image much smaller than the default build
RUN pip install --no-cache-dir --default-timeout=300 --retries 10 \
    torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --default-timeout=300 --retries 10 \
    kokoro soundfile fastapi "uvicorn[standard]"
RUN python -m spacy download en_core_web_sm

ENV HF_HOME=/cache/hf
WORKDIR /app
COPY tts_app.py .

EXPOSE 8001
CMD ["uvicorn", "tts_app:app", "--host", "0.0.0.0", "--port", "8001"]
```

#### `tts/tts_app.py`

```python
import base64, io, os

import numpy as np
import soundfile as sf
from fastapi import FastAPI
from pydantic import BaseModel

SAMPLE_RATE = 24000
app = FastAPI()
_pipeline = None


class SpeakRequest(BaseModel):
    text: str
    voice: str = os.getenv("TTS_VOICE", "af_heart")


def pipeline():
    global _pipeline
    if _pipeline is None:
        from kokoro import KPipeline
        _pipeline = KPipeline(lang_code="a")  # American English
    return _pipeline


def has_word(s):
    return any(ch.isalnum() for ch in s)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/speak")
def speak(req: SpeakRequest):
    parts, words, offset = [], [], 0.0
    for result in pipeline()(req.text, voice=req.voice):
        if result.audio is None:
            continue
        audio = np.asarray(result.audio, dtype=np.float32)

        for tok in (getattr(result, "tokens", None) or []):
            text = tok.text
            # Punctuation sticks to the previous word ("trick" + "," -> "trick,")
            if not has_word(text):
                if words:
                    words[-1]["w"] += text
                continue
            s, e = tok.start_ts, tok.end_ts
            if s is None or e is None:
                abs_s = words[-1]["e"] if words else offset
                abs_e = abs_s + 0.25
            else:
                abs_s, abs_e = offset + s, offset + e
            words.append({"w": text, "s": round(abs_s, 3), "e": round(abs_e, 3)})

        parts.append(audio)
        offset += len(audio) / SAMPLE_RATE

    audio = np.concatenate(parts)
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV")
    return {
        "duration": len(audio) / SAMPLE_RATE,
        "words": words,
        "audio_b64": base64.b64encode(buf.getvalue()).decode(),
    }
```

#### `renderer/Dockerfile`

```dockerfile
FROM manimcommunity/manim:stable

USER root
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

WORKDIR /app
COPY app.py shorts_base.py ./

USER 1000:1000
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### `renderer/app.py`

```python
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
    """Strip Manim's decorative boxes so errors are plain text."""
    lines = []
    for line in BOX_CHARS.sub("", text).splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)[-limit:]


def synth(text, voice):
    """Ask the tts service for one line. Returns (wav bytes, duration, words)."""
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
        out.append({
            "text": text,
            "audio": str(wav),
            "duration": round(meta["duration"], 3),
            "words": meta["words"],
        })
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

    final = d / "final.mp4"
    shutil.move(str(out), final)
    return {
        "ok": True,
        "job_id": jid,
        "video_path": f"/files/renders/{jid}/final.mp4",
        "duration": video_duration(final),
        "narration_seconds": round(sum(s["duration"] for s in narration), 2),
    }
```

**API contract:**

- `POST /render` takes `{code, scene="Main", job_id, segments: [str], voice?}`.
- On success it returns `{ok: true, job_id, video_path, duration, narration_seconds}`.
- On failure it returns `{ok: false, job_id, stage: "input"|"tts"|"render", error}`. Only `stage: "render"` errors go to the LLM repair loop.

#### `renderer/shorts_base.py`

```python
"""Shared template for every Short. Generated scenes start with:
    from shorts_base import *
"""
import json
from contextlib import contextmanager
from pathlib import Path

from manim import *

# 9:16 frame: 4.5 units wide, 8 units tall, origin at the centre
config.frame_height = 8
config.frame_width = 4.5
config.background_color = "#0f1117"

# Palette
ACCENT = "#4fc3f7"    # blue: main highlight
ACCENT_2 = "#ffb74d"  # orange: second item / contrast
ACCENT_3 = "#81c784"  # green: results / "correct"
MUTED = "#9e9e9e"     # grey: secondary text

# Layout. YouTube's own buttons and title cover the bottom and right edges,
# so all content stays within these bounds.
SAFE_WIDTH = 4.0
CONTENT_TOP = 3.4
CONTENT_BOTTOM = -1.4
CAPTION_Y = -2.1

# Caption lines
MAX_CAPTION_CHARS = 20
MAX_CAPTION_WORDS = 4


def fit(mob, max_width=SAFE_WIDTH):
    """Shrink a mobject to fit the safe width. Returns it for chaining."""
    if mob.width > max_width:
        mob.scale_to_fit_width(max_width)
    return mob


def _estimate_words(seg):
    """Fallback when the voice gave no word timings: spread words by length."""
    words = seg["text"].split()
    total = sum(len(w) for w in words) or 1
    out, acc = [], 0
    for w in words:
        s = seg["duration"] * acc / total
        acc += len(w)
        out.append({"w": w, "s": s, "e": seg["duration"] * acc / total})
    return out


def _caption_chunks(seg):
    """Group timed words into short caption lines: [(text, start_time), ...]."""
    words = seg.get("words") or _estimate_words(seg)
    chunks, cur = [], []
    for w in words:
        candidate = " ".join(x["w"] for x in cur + [w])
        if cur and (len(candidate) > MAX_CAPTION_CHARS or len(cur) >= MAX_CAPTION_WORDS):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if w["w"] and w["w"][-1] in ".,!?;:":
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return [(" ".join(x["w"] for x in c), c[0]["s"]) for c in chunks] or [("", 0.0)]


def _caption(text):
    cap = Text(text, font_size=26, weight=BOLD, color=WHITE)
    cap.set_stroke(BLACK, width=5, background=True)
    fit(cap)
    return cap.move_to(UP * CAPTION_Y)


class ShortScene(Scene):
    pad = 0.25  # short pause after each segment, in seconds

    def setup(self):
        data = json.loads(Path("narration.json").read_text(encoding="utf-8"))
        self.segments = data["segments"]

    @contextmanager
    def say(self, i):
        """Play narration segment i with captions. Yields its duration."""
        seg = self.segments[i]
        dur = seg["duration"]
        start = self.renderer.time
        self.add_sound(seg["audio"])

        # One caption object per line, all created up front. Inactive lines
        # are parked off-screen so the set of objects never changes mid-play.
        chunks = _caption_chunks(seg)
        starts = [s for _, s in chunks]
        off_screen = UP * 50
        caps = [_caption(text) for text, _ in chunks]
        for c in caps[1:]:
            c.move_to(off_screen)
        state = {"idx": 0}
        holder = VGroup(*caps)

        def update(m):
            t = self.renderer.time - start
            idx = 0
            for k, s in enumerate(starts):
                if s <= t:
                    idx = k
            if idx != state["idx"]:
                caps[state["idx"]].move_to(off_screen)
                caps[idx].move_to(UP * CAPTION_Y)
                state["idx"] = idx

        holder.add_updater(update)
        self.add(holder)
        try:
            yield dur
        finally:
            remaining = dur + self.pad - (self.renderer.time - start)
            if remaining > 0.02:
                self.wait(remaining)
            holder.clear_updaters()
            self.remove(holder)
```

#### `example_gauss.py` (smoke test only, below the target difficulty)

```python
from shorts_base import *


class Main(ShortScene):
    def construct(self):
        with self.say(0) as d:
            title = Text("Gauss's Trick", font_size=44, color=ACCENT)
            title.move_to(UP * 3)
            self.play(Write(title), run_time=min(1.5, d * 0.9))

        with self.say(1) as d:
            total = fit(MathTex(r"1 + 2 + 3 + \cdots + 100", font_size=44))
            total.move_to(UP * 1.5)
            self.play(Write(total), run_time=d * 0.7)

        with self.say(2) as d:
            fwd = MathTex(r"1 + 2 + \cdots + 100", font_size=38)
            bwd = MathTex(r"100 + 99 + \cdots + 1", font_size=38, color=ACCENT_2)
            rows = fit(VGroup(fwd, bwd).arrange(DOWN, buff=0.4)).move_to(UP * 1.5)
            self.play(ReplacementTransform(total, fwd), run_time=d * 0.4)
            self.play(FadeIn(bwd, shift=UP * 0.3), run_time=d * 0.4)

        with self.say(3) as d:
            line = Line(LEFT * 1.8, RIGHT * 1.8).next_to(rows, DOWN, buff=0.3)
            sums = MathTex(r"101 + 101 + \cdots + 101", font_size=38, color=ACCENT)
            fit(sums).next_to(line, DOWN, buff=0.3)
            self.play(Create(line), run_time=d * 0.2)
            self.play(Write(sums), run_time=d * 0.6)

        with self.say(4) as d:
            self.play(FadeOut(VGroup(title, rows, line, sums)), run_time=d * 0.2)
            result = MathTex(r"\frac{100 \times 101}{2} = 5050", font_size=48)
            result.move_to(UP * 1.5)
            box = SurroundingRectangle(result, color=ACCENT_3, buff=0.2)
            self.play(Write(result), run_time=d * 0.5)
            self.play(Create(box), run_time=d * 0.2)

        with self.say(5) as d:
            general = fit(MathTex(r"1 + 2 + \cdots + n = \frac{n(n+1)}{2}",
                                  font_size=44))
            general.move_to(UP * 1.5)
            self.play(FadeOut(box), ReplacementTransform(result, general),
                      run_time=d * 0.6)
```

#### `test_phase3.py`

```python
import json, time, urllib.request

segments = [
    "Here's a trick a ten-year-old supposedly used to stun his teacher.",
    "Add up every number from one to a hundred.",
    "Write the list forwards, then write it again backwards underneath.",
    "Each column adds up to one hundred and one, and there are a hundred columns.",
    "That counts everything twice, so halve it: five thousand and fifty.",
    "And it works for any n: n times n plus one, all over two.",
]
body = json.dumps({
    "code": open("example_gauss.py", encoding="utf-8").read(),
    "scene": "Main",
    "job_id": "gauss",
    "segments": segments,
}).encode()
req = urllib.request.Request("http://localhost:8000/render", data=body,
                             headers={"Content-Type": "application/json"})
start = time.time()
print(json.dumps(json.loads(urllib.request.urlopen(req, timeout=1200).read()), indent=2))
print(f"took {time.time() - start:.1f}s")
```

### 8.3 Standard rebuild and test sequence

```bash
cd ~/shorts-pipeline
docker compose up -d --build renderer tts
until curl -s http://localhost:8000/health > /dev/null; do sleep 1; done
python3 test_phase3.py
head -c 600 data/renders/gauss/narration.json    # should show "words" with timings
```

**Result at handover:** the render succeeds, voice and animation sync is accurate, and captions are word-timed with no overlap. The owner reports it "working more or less fine". Fine-tune captions via the constants at the top of `shorts_base.py` (`MAX_CAPTION_CHARS`, `MAX_CAPTION_WORDS`, `CAPTION_Y`, font size in `_caption`).

---

## 9. Gotchas and lessons learned

1. **The Manim image is Python 3.14.** Many ML packages, Kokoro included, don't support it. Never install ML or TTS libraries into the renderer; put them in separate services.
2. **There is no `ffprobe` in the Manim image.** Newer Manim uses PyAV. Use `av` for media inspection.
3. **pip timeouts on large wheels** (PyTorch): use `--default-timeout=300 --retries 10`.
4. **Manim snapshots "moving mobjects" at the start of each `play()`.** Adding or removing submobjects in an updater mid-animation leaves stale objects drawn until the animation ends. The fix is to create everything up front and move or hide it, never swap it.
5. **Character-count caption timing drifts** at pauses and with spoken numbers. Use Kokoro's token `start_ts` and `end_ts`.
6. **`@contextmanager` without a `yield` produces `'NoneType' object is not an iterator`.** This happens when an edit loses or mis-indents the `try: yield` block.
7. **Readiness race:** testing straight after `up -d` can give `Connection reset by peer`. Wait on `/health` first.
8. **A failed build leaves the old container running,** so errors can come from stale code. Check the `CREATED` column in `docker compose ps`.
9. **Run Compose from Ubuntu,** not PowerShell on a `\\wsl.localhost` path. Otherwise `.env` isn't read.
10. **Unhandled exceptions in FastAPI become bare 500s.** Every step must return structured `{ok, stage, error}` so n8n can decide what to do.
11. **First TTS call downloads the Kokoro model** (hundreds of MB) into the `tts_cache` volume. The first render is slow.

---

## 10. Open items to verify before Phase 4

**Status as of 5 Oct 2026 (Claude Code session):**

- ✅ Item 1 resolved: `.env` had Windows CRLF line endings, so every value carried an invisible `\r` and the key compared as MISMATCH. Fixed with `sed -i 's/\r$//' .env`; now MATCH (`scripts/check_n8n_key.sh`). **If `.env` is ever edited in a Windows editor again, re-run that script.**
- ⚠️ Item 2 partly resolved: the owner created **five per-step Gemini keys** from different Google accounts (`GEMINI_API_KEY_TOPIC`, `_SCRIPT_CHECK`, `_CODE`, `_REPAIR`, `_METADATA`). All five list all three planned models, but **TOPIC and SCRIPT_CHECK are hard-denied on `generateContent`** ("Your project has been denied access", PERMISSION_DENIED) — those two keys must be replaced. CODE, REPAIR and METADATA work (`scripts/verify_keys.py`, `scripts/debug_gemini_403.py`).
- ✅ Item 3 resolved: HF token works through the OpenAI-compatible router; Llama-3.3-70B responds. Note: requests need a `User-Agent` header or Cloudflare returns 403.
- ✅ Item 4 resolved (five keys + HF_TOKEN present).
- ⏸ Items 5 and 6 still owner tasks (publishing test posts; GitHub Pages wording).
- ✅ Item 7 resolved: git initialized on `main` with the Section 20 `.gitignore`; no remote yet.
- ✅ Item 8 resolved: second-run `test_phase3.py` took **38.7s** for a 25.7s video; the three Phase 4 example scenes took 98–139s each for ~40s videos. The 900s render timeout has ample headroom.

1. **n8n encryption key:** confirm `.env` has a line named exactly `N8N_ENCRYPTION_KEY` whose value matches `docker compose exec n8n cat /home/node/.n8n/config`. Confirm `docker compose up -d` shows no "variable is not set" warning, and that the YouTube credential in n8n is still connected.
2. **Gemini models available on the owner's key:** check `gemini-3.8-flash`, `gemini-3.5-flash-lite` and `gemini-3.1-pro-preview` in AI Studio or with a test call, and check free-tier limits for each.
3. **Hugging Face token:** fine-grained, with the "Make calls to Inference Providers" permission. Add it to `.env` as `HF_TOKEN`. Confirm `meta-llama/Llama-3.3-70B-Instruct` is served by some provider through the router, and check the monthly free credits; these are small.
4. **`.env` additions:** `GEMINI_API_KEY`, `HF_TOKEN`.
5. **Publishing services:** confirm the test posts appeared **public** (Phase 1, Step 5), and check whether free quotas reset on the calendar month or the signup date.
6. **GitHub Pages wording:** "Math" → "STEM".
7. **Version control:** initialize git with the `.gitignore` in Section 20, and push to a private repo for now. Make it public later for the resume, after confirming no secrets are present.
8. **Render time:** record the second-run time of `test_phase3.py` (not yet reported) to size timeouts and schedules.

---

## 11. Phase 4: Prompts and the Python test harness ⏳ NEXT

**Goal:** working prompts for topic, script, fact-check, code, repair and metadata, tuned outside n8n, plus an evaluation harness that measures success rates.

### 11.1 Deliverables

```
prompts/
├── topic.md
├── script.md
├── factcheck.md
├── code.md
├── repair.md
└── metadata.md
examples/                     (3 university-level, v1-style example scenes, each with its segments)
├── ex1_<topic>.py + ex1_<topic>.json
├── ex2_<topic>.py + ex2_<topic>.json
└── ex3_<topic>.py + ex3_<topic>.json
pipeline_test.py
data/state/history.json       (topics already covered; seeded empty)
data/experiments/<run_ts>/    (harness output)
```

Prompts live in files so n8n (Phase 5) and the harness use the **identical text**.

### 11.2 Data contracts (JSON)

**Topic output:**

```json
{
  "category": "ai_ml | math | physics | chemistry | electrical | mechanical | cs_algorithms | networking_it | web_dev | other_science",
  "level": "university | high_school",
  "topic": "How attention weights are computed",
  "key_idea": "Each token scores every other token with a dot product, then softmax turns the scores into weights.",
  "hook": "One question in 10 words or fewer to open the video"
}
```

Inputs: the full history list (topic and category), and the category-rotation rule: don't repeat the previous 2 categories, and aim for roughly 85% university and 15% high school.

**Script output (contract between the script, code and render steps):**

```json
{
  "topic": "...",
  "segments": [
    {"narration": "spoken text", "visual": "what appears on screen"}
  ]
}
```

Script rules:

- 10 to 14 segments, totalling **185 to 215 words** (about 70 to 80 seconds at the measured ~0.37 s/word Kokoro pace). Calibrate against `narration_seconds` from real renders.
- At least 3 segments must explain the **mechanism** (why the fact holds), not just state it.
- Narration is **spoken text only**: no LaTeX, symbols, code syntax or markdown. Write "x squared", "O of n log n", "e to the i pi". The TTS reads exactly what's written.
- 8 to 20 words per segment. Segment 0 is the hook. One core idea. The last segment lands the payoff, with no "like and subscribe".
- `visual` must be **concrete and feasible in Manim v1**: an equation, a short text label, axes with a plotted function, arrows, boxes and circles, a small graph or tree, a matrix, a code snippet of 6 lines or fewer, bars. No photos, 3D, maps or real-world imagery.

**Fact-check output:**

```json
{"ok": true, "issues": [], "segments": [ ...corrected segments, same shape... ]}
```

If `ok` is false and the issues are serious, regenerate the script, at most twice. Otherwise use the corrected segments.

**Metadata output:**

```json
{
  "title": "50 to 70 characters, accurate, no clickbait",
  "description": "2 to 3 sentences explaining the idea, then a blank line, then 3 to 5 hashtags including #Shorts",
  "tags": ["..."]
}
```

### 11.3 Code prompt rules (`prompts/code.md`)

Give the model: a concise **API summary of `shorts_base`** (the constants, `fit()`, `ShortScene`, `say()`), the rules below, the **three example scenes with their segments**, and the new segments.

Rules:

1. Start with `from shorts_base import *`. Define exactly **`class Main(ShortScene)`** with `construct(self)`.
2. Use **one `with self.say(i) as d:` block per segment, in order, each index exactly once**, covering all segments.
3. In each block, the sum of `run_time`s must be **at most 0.9 × d**. Express run times as fractions of `d`.
4. Keep content within `CONTENT_BOTTOM` ≤ y ≤ `CONTENT_TOP`, and keep widths within `SAFE_WIDTH` using `fit()`. **Never draw captions**; the template does that.
5. Use only the palette constants and `WHITE`/`MUTED` for colour.
6. Math goes in `MathTex` (raw strings); prose goes in `Text`. Never put LaTeX in `Text`.
7. Code snippets: check the installed Manim's `Code` signature first (it changed in v0.19), keep to 6 lines or fewer, and use a small font.
8. Plots: `Axes` with explicit small ranges, then `plot()`. Keep it simple.
9. **No 3D scenes, external files, images, network access, randomness without a seed, or imports** beyond `shorts_base`, `numpy` and `math`.
10. Show at most 3 to 4 elements at once. Clear the stage (`FadeOut`) before a new layout.
11. Output **only** a single fenced Python code block.

### 11.4 Static checks before rendering (cheap; add to the harness and later the renderer)

- `ast.parse` succeeds.
- `class Main(ShortScene)` exists.
- The `say(` indices are exactly `0..n-1`, each used once, where n is the number of segments.
- Imports are only from the allowed set.
- No `open(`, `exec(`, `eval(`, `__import__`, `subprocess` or `os.` in the code.
- Failures are fed to the repair prompt just like render errors, without spending a render.

**Recommended:** add a `POST /validate` endpoint to the renderer running these checks, so n8n can use it in Phase 5.

### 11.5 Repair loop

- Input: the segments, the failing code, the cleaned error (`stage: "render"` only), and the same rules.
- Output: full corrected code.
- **At most 3 repair attempts.** Then mark the job failed (alert in Phase 7) and move on. The queue covers the gap.
- `stage: "tts"` errors do **not** go to the LLM: retry once, then alert.

### 11.6 Example scenes (Claude Code writes these, renders them and gets owner approval)

These replace Gauss as the style examples, at university level, one domain each. Suggestions:

1. **Math:** eigenvectors as directions a matrix only stretches (`NumberPlane`, vectors, `ApplyMatrix`).
2. **AI/ML:** attention weights via dot products and softmax (a small matrix of scores, then bars).
3. **Engineering/physics:** RC circuit charging, V(t) = V₀(1 − e^(−t/RC)) (`Axes`, plot, a marked τ).

Each example needs its own segments JSON (in the script contract format), must render cleanly, and must respect every rule in 11.3. **Have the owner watch each one before it's used as an example.**

### 11.7 `pipeline_test.py` specification

- Runs in an Ubuntu venv: `python3 -m venv .venv && . .venv/bin/activate`. Uses `requests` and `python-dotenv`, or only the standard library.
- Reads `GEMINI_API_KEY` and `HF_TOKEN` from `.env`. **Never prints keys.**
- CLI examples:
  - `python pipeline_test.py --n 5`
  - `python pipeline_test.py --topic "How DNS resolution works"`
  - `--category ai_ml`, `--code-model gemini-3.1-pro-preview`
- Per run: topic → script (Llama) → fact-check → static checks → render → repair loop → metadata. Save everything to `data/experiments/<run_ts>/<job_id>/`: `topic.json`, `script.json`, `factcheck.json`, `scene_attempt{k}.py`, `render_attempt{k}.json`, `metadata.json`, `final.mp4` path.
- Do **not** write to `history.json` during experiments, unless run with `--commit`.
- Print a summary table: topic, first-try success, attempts used, final success, video duration, narration seconds, wall time, and per-model call counts.
- Also write `summary.json` for the resume metrics.

**API calls (verify against current docs before coding):**

- Gemini REST: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent` with header `x-goog-api-key: $GEMINI_API_KEY`. Use `generationConfig.responseMimeType = "application/json"` (optionally with `responseSchema`) for the JSON steps.
- Hugging Face, OpenAI-compatible router: `POST https://router.huggingface.co/v1/chat/completions` with `Authorization: Bearer $HF_TOKEN` and model `meta-llama/Llama-3.3-70B-Instruct`. A provider suffix may be needed. Ask for JSON and validate it; retry on parse failure.
- Add retries with backoff on 429 and 5xx for all LLM calls.

### 11.8 Exit criteria for Phase 4

- On a batch of **20 varied topics**: final render success of at least 85% after repairs, and first-try success measured and recorded.
- Durations within 65 to 90 seconds for 90% or more of videos.
- The owner has watched at least 5 outputs, and they're accurate and look good.
- Prompts frozen in `prompts/`, with the metrics saved.

---

### 11.9 Phase 4 progress (5 Oct 2026)

Built and verified in the Claude Code session:

- **All six prompts** in `prompts/` with `{{PLACEHOLDER}}` tokens (filled identically by the harness now and n8n later).
- **Three example scenes** in `examples/` (eigenvectors, attention, RC circuit), each with its segments JSON. All three rendered **first try**: 40.4s / 41.2s / 40.4s, render times 98–139s. **The owner has not yet watched them — required before they're trusted as style examples.**
- **`pipeline_test.py`** per spec 11.7, stdlib only (no venv needed). Key mapping: one env var per step (`GEMINI_API_KEY_TOPIC`, `_SCRIPT_CHECK`, `_CODE`, `_REPAIR`, `_METADATA`), with OS environment overriding `.env`. Models: topic/metadata `gemini-3.5-flash-lite`, factcheck/code/repair `gemini-3.8-flash` (`--code-model` overrides code+repair), script Llama-3.3-70B via HF router.
- `data/state/history.json` seeded empty; `data/experiments/` created.
- Helper scripts in `scripts/`: `check_n8n_key.sh`, `verify_keys.py`, `debug_gemini_403.py`, `render_example.py`, `test_llm_steps.py`, `run_harness_remapped.sh` (temporary — routes the two denied keys to working ones), `commit.sh`.

**Blocked on the owner:** replace the denied TOPIC and SCRIPT_CHECK keys, watch the three example videos, then run the 20-topic batch (11.8).

### 11.10 Later the same day (5 Oct 2026): format retarget and quota findings

**Owner feedback after watching the first renders:** captions floated with dead
space below them, content crowded the top and overlapped (worst in the RC video),
and 45s was too shallow to explain anything properly.

Changes made:

1. **Layout** (`renderer/shorts_base.py`): `CAPTION_Y` −2.1 → **−2.75**,
   `CONTENT_BOTTOM` −1.4 → **−2.1**. Content now uses ~69% of frame height.
   The code/repair prompts additionally prescribe **vertical bands** (title ≈3.1,
   persistent reference 1.8–2.6, working visual −0.8–1.5, equations −1.3–−2.0)
   and forbid two objects sharing a band unless positioned together. The renderer
   image must be rebuilt when `shorts_base.py` changes (it is COPY'd in).
2. **Length:** target ~75s. Script prompt: 10–14 segments, 185–215 words, with
   at least 3 "mechanism" segments. Harness duration window now 65–90s.
3. **Examples** rewritten to the new standard (~190 words, 12–13 segments each)
   and re-rendered. **Owner approval still pending.**

Quota facts learned (important for Phase 5 scheduling):

- Gemini free tier is **20 requests/day/project on `gemini-3.8-flash`** (hit the
  limit during testing; error names the metric and limit). Flash-lite limits are
  far higher. One video/day fits easily; same-day batch tests do not.
- `gemini-3.1-pro-preview` returns **429 instantly** on these keys — a consumer
  "Google AI Pro" subscription does **not** grant API quota. The "Pro if Flash
  underperforms" option in 2.2 needs a billed API project instead.
- 3.8-flash shows intermittent model-wide **503 "high demand"**; the harness
  retries with backoff (7 tries, up to 120s) and the light steps (topic,
  factcheck, metadata) fall back one model when saturated. Code/repair never
  fall back.
- The owner's **replacement TOPIC and SCRIPT_CHECK keys are still denied**
  ("project has been denied access") — same error as the originals. Two denied
  projects in a row suggests Google is flagging the account pattern; if the next
  replacement is also denied, consider consolidating steps onto the three
  working keys instead (the per-step env-var layout makes that a `.env`-only change).
- 20-topic batch: owner decided **not** to run it for now.

### 11.11 Provider migration (5 Oct 2026, evening): Groq + OpenRouter

The denied-key and quota problems were solved by moving the light steps off
Gemini entirely. The owner added `GROQ_API_KEY` and `OPENROUTER_API_KEY` to `.env`.

**New model split** (replaces the table in 2.2 for the affected steps; specs are
`provider:model` for OpenAI-compatible providers, bare names for Gemini):

| Step | Model | Why |
|---|---|---|
| Topic | `groq:openai/gpt-oss-20b` | Groq free tier: 1,000 req/day |
| Script | `groq:openai/gpt-oss-120b` | **Llama 3.3 is gone from Groq's catalog**, and HF free credits are $0.10/month (effectively nothing), so the original Llama-via-HF plan is dead. gpt-oss-120b is the strongest free writer available. |
| Fact-check | `groq:qwen/qwen3.8-27b` | Different model family from the script writer; caught a real subtlety in testing |
| Code | `gemini-3.8-flash` (CODE key) | 20 req/day free is enough for production |
| Repair | follows the code model (REPAIR key when Gemini) | |
| Metadata | `gemini-3.5-flash-lite` (METADATA key) | That key works and flash-lite limits are high |

- Free code alternative, also used for A/B metrics:
  `--code-model "openrouter:nvidia/nemotron-3-ultra-550b-a55b:free"` (OpenRouter free: 50 req/day, or 1,000/day after a one-time $10 top-up).
- Saturation fallbacks all stay within Groq (qwen ↔ gpt-oss variants).
- The denied `GEMINI_API_KEY_TOPIC` / `GEMINI_API_KEY_SCRIPT_CHECK` are now unused
  (kept in `.env` in case Google un-denies them); `HF_TOKEN` is unused as well.
- `scripts/list_provider_models.py` lists Groq's catalog and OpenRouter's
  zero-priced models; provider catalogs change often, so re-run it before
  changing any model spec.
- Script prompt now also bans parentheses and coordinate tuples in narration
  (gpt-oss slipped "(0,1)"-style text past the earlier wording).

### 11.12 Owner review of the first machine video (5 Oct 2026): quality hardening

The first end-to-end machine-generated video (KMP, Nemotron code, 90.1s) rendered
first-try but the owner rejected it: content spilled out of frame, stale elements
stayed under new ones, and the script launched into KMP with no context. Fixes,
in three layers:

1. **Mechanical bounds enforcement** (not just prompt rules): `ShortScene` now
   measures every mobject's bounding box at the end of each segment
   (`_check_bounds`, slack 0.15 over the layout constants) and writes
   `bounds_violations.json`; the renderer **fails the job** with a per-segment,
   per-edge error (e.g. "segment 4: Axes right edge x=2.60 > 2.15"), which the
   repair loop consumes. A visually broken render is now a *failed* render.
2. **Stage management**: new template helper `self.sweep(*keep, run_time=0.4)`
   fades out everything on stage except `keep` (captions immune via an
   `_is_caption` mark). Code/repair prompts require it when a segment lays out
   new visuals; examples demonstrate it.
3. **Hook-driven scripts**: the topic "hook" is now a concrete real-world
   scenario (10–18 words, app/device/everyday life — never an abstract question),
   and the script rules require: segments 0–1 set up that scenario jargon-free,
   every term defined before use ("assume the viewer has never heard of this"),
   the whole explanation anchored to the scenario, and the final segment
   resolving it. Ex1's hook was reworked to the PageRank framing to model this.

Note: the renderer image must be rebuilt for template changes; the example
renders double as a regression test of the bounds checker (they must pass it).

### 11.13 Layout hardening round 2 + code-model verdict (5–7 Oct 2026)

The first bounds checker had a blind spot: it skipped containers (`Text`,
`MathTex`, `VGroup` report no points of their own), so text leaked unchecked —
cause of the rejected CLT video. Fixed with `family_members_with_points()`.
Further hardening from the owner's review: caption font 26→24; hard font
ceilings in prompts (title ≤36, equations 28–32, body 22–26, labels 18–22);
boxes around text must be `SurroundingRectangle`, never fixed-size rectangles;
the script prompt locks visuals to a literal primitive vocabulary (no "icons" —
a coin is a circle labelled H) described as layout instructions; example fonts
rescaled; ex3's 63% label moved inside the axes (caught by the fixed checker).

**Code-model verdict (tested on the same fact-checked CLT script):**
`gemini-3.8-flash` succeeded **first try with zero repairs** under all the new
rules; the free OpenRouter models (nemotron ultra/super) needed many calls and
kept failing on endpoint flakiness (truncation via `finish_reason: length`,
IncompleteRead, overload) even with a 16k token budget and low reasoning effort.
Decision (owner: no paid APIs): **Gemini 3.8-flash is the code/repair model;
OpenRouter free models are the fallback** for saturated days. Research context:
published Manim-generation work reaches ~94% render success using exactly this
architecture (constrained API + static checks + renderer-in-the-loop repair), so
the ≥85% Phase 4 exit target is realistic.

Testing economics: `--reuse <experiment job dir>` replays a saved script, so a
code-prompt iteration costs exactly 1 code call against the 20/day Gemini cap.

---

## 12.9 Phase 5 as actually built (GitHub Actions), and the launch checklist

**Architecture decision (7 Oct 2026):** production runs on GitHub Actions, not
n8n, so the owner's PC never needs to be on. The n8n container remains for local
experimentation only. Repo: **private**, `github.com/AadityaKaushik/shorts-pipeline`
(`gh` CLI authenticated in WSL). Secrets: one Actions secret `DOTENV` (the `.env`
minus the n8n key). The **queue lives in GitHub Releases** (`queue-<name>` tags,
oldest-first by tag sort); `data/state/history.json` and `publish_log.json` are
committed back by the workflows (`git add -f`, since `data/` is gitignored).

- `.github/workflows/daily.yml` — 07:00 IST (01:30 UTC): publish oldest queue
  release via `scripts/publish_daily.py`, delete the release, then generate one
  video (containers built in the runner) and upload it as a new release.
- `.github/workflows/topup.yml` — 13:00 IST: generate only if queue < 5.
- `docker-compose.ci.yml` — CI overrides: 2-CPU/low-RAM limits (private-repo
  runners have 2 vCPU / 7 GB), TTS model cache bind-mounted for actions/cache.
- CI gotchas fixed: runner uid is 1001 vs container's 1000 → `chmod -R a+rwX
  data ci-cache` before compose up; failure steps dump container logs.
- `scripts/generate_daily.py` — production generation (queue-cap → pipeline →
  `/package`). `scripts/publish_daily.py` — oldest-from-queue, monthly routing
  (1–10 Upload-Post, 11–30 bundle.social, then hold), `--dry` mode, failures
  keep the video queued. bundle.social still needs `BUNDLE_SOCIAL_TEAM_ID` in `.env`.
- Cloud test status: third manual run passed container startup and was then
  deliberately cancelled; **both workflows are disabled** (`gh workflow disable`)
  and **nothing has ever been posted**.

**Launch checklist (owner returns after exams, ~mid-Oct 2026):**

1. Owner drops `assets/intro.mp4` (4–5s), `assets/outro.mp4` (4–5s), and
   `assets/music.mp3` into the project — same files for every video.
2. Build the post-processing step (ffmpeg in the renderer image): normalize
   intro/outro to 1080×1920@30, concat intro+video+outro, mix music low under
   narration with end fade-out; skip silently when assets are missing.
3. Re-process the 5 chosen starter videos through it: ex1 eigenvectors,
   ex2 attention, ex3 RC circuit, Fourier, convolution (owner-approved picks).
4. Generate `metadata.json` for the 3 examples (flash-lite), owner reviews titles.
5. Seed 5 queue releases; verify `UPLOAD_POST_PROFILE` matches the dashboard
   profile name (currently `default` — confirm).
6. Re-enable workflows (`gh workflow enable daily.yml topup.yml`), watch the
   first scheduled cycle, confirm the first post appears PUBLIC on the channel.
7. Then: Phase 7 alerts, handover cleanup, repo public after a fresh secret scan.

---

## 12. Phase 5: Generation workflow (n8n) — SUPERSEDED by 12.9; kept for reference

**Principle:** n8n handles scheduling, LLM HTTP calls and branching. **Logic-heavy steps live in Python endpoints** (validate, render, package): they're easier to test, and they put real code in the repo.

### 12.1 New renderer endpoints

- `POST /validate`: the static checks from 11.4, returning `{ok, errors}`.
- `POST /package`: given `job_id`, topic, script, metadata and attempts, copies `final.mp4` and the artifacts to `data/queue/<YYYY-MM-DD>_<slug>/` and appends to `data/state/history.json`. Returns the folder path.

**Queue folder format:**

```
data/queue/2026-10-12_attention-weights/
├── video.mp4
├── metadata.json
├── topic.json
├── script.json
├── scene.py          (final working code)
└── render.log        (all attempts and errors)
```

### 12.2 Workflow "Generate Short"

1. **Schedule trigger:** daily, at a time the PC is reliably on. Agree the time with the owner.
2. **Check the queue size:** if it already holds 5 or more videos, stop. Target buffer: 3 to 5.
3. **Read** `history.json`.
4. **Topic** (Gemini Flash-Lite, JSON).
5. **Script** (Llama 3.3, JSON), then **fact-check** (Gemini).
6. **Code** (Gemini), then `/validate`, then `/render`. On failure (stage `render` or validation), run **repair**, looping at most 3 times with a counter.
7. On success: **metadata** (Gemini), then `/package`.
8. On final failure: write a failure record and trigger an alert (Phase 7).

Use the same prompt files as Phase 4. Mount `prompts/` into n8n if needed, or paste their contents into nodes, keeping a single source of truth.

### 12.3 Optional human-in-the-loop

- **Weekly topic backlog:** a workflow generates about 10 candidate topics and sends them to the owner (Telegram) for approval. Approved topics go into `data/state/backlog.json`, and generation draws from the backlog first.
- **Queue review:** the owner can delete a queued folder to veto a video.

---

## 13. Phase 6: Publishing workflow

1. **Schedule trigger:** daily at the chosen publish time (for example evening IST).
2. Pick the **oldest** folder in `data/queue/`.
3. Read `data/state/publish_log.json`, count this month's successful posts, and route: fewer than 10 through **Upload-Post**, 10 to 29 through **bundle.social**, 30 or more means hold and alert.
4. Upload the video with title, description and tags. **Check each provider's API docs for exact fields** (file upload, YouTube title and description, privacy public). Both have n8n integrations or plain HTTP APIs.
5. On success: move the folder to `data/published/`, and log the date, provider, video URL and folder.
6. On failure: retry once with the other provider if it has quota, then alert.
7. **Audit evidence branch** (temporary, about a week): also upload through **our own** Google project with n8n's YouTube node. Uploads are locked private, which is expected. This produces real API usage, private videos on the channel, and screenshots for the audit.

YouTube settings: category **Education (27)**; not made for kids; **disclose synthetic media** where the option is available (the Data API has `status.containsSyntheticMedia`).

---

## 14. Phase 7: Alerts

- Telegram bot (via BotFather) with n8n's Telegram node, or email.
- Alert on: a generation job failing after 3 repairs; the queue dropping below 2; a publish failing; the tts or renderer health check failing; the YouTube OAuth credential erroring.
- Use an n8n **Error Trigger** workflow to catch unhandled workflow errors.
- Optional: a weekly summary (videos published, success rates, queue depth).

---

## 15. Phase 8: Dry run, go live, audit

1. Run generation only for **7 days**. The owner watches every video, and prompts get fixed as issues appear.
2. Turn publishing on. Confirm the first Short is **public** and classified as a Short (vertical, under 3 minutes).
3. **Submit the YouTube API audit** (YouTube API Services audit form, reachable from the Data API docs and the Cloud Console):
   - Project number, and the client (the n8n workflow on the owner's own PC).
   - The use case, described plainly: *a personal internal tool that uploads the developer's own original educational animations to the developer's single YouTube channel, about one video a day, with no other users and no data collected.*
   - Links to the homepage and privacy policy.
   - Screenshots: the n8n workflow, the YouTube credential, privacy-locked test uploads, and a sample video.
   - Be honest about automation. Misrepresenting a client is itself a policy violation.
4. Expect weeks, possibly months. Keep publishing through the interim services meanwhile.

---

## 16. Phase 9: After the audit passes

1. Replace the publishing branch with n8n's **YouTube → Upload** node using our credential: privacy public, category 27, made-for-kids false, synthetic media disclosed.
2. Confirm with one upload that it is **public**.
3. Remove the Upload-Post and bundle.social branches and cancel any paid plans.
4. Keep the queue, alerts and archive unchanged.

---

## 17. Monetization and policy notes (secondary goal)

Figures are from secondary sources as of October 2026; check YouTube Studio → Earn for current numbers.

- **Full Partner Program (ad revenue):** 1,000 subscribers, plus 4,000 watch hours in 12 months **or** 10 million Shorts views in 90 days.
- **Lower tier (fan funding and shopping):** 3 million Shorts views.
- **From February 2027, new entrants** reportedly need 8,000 watch hours or 20 million Shorts views in 90 days. Plan around the higher bar.
- **The July 2025 "inauthentic content" policy** targets mass-produced AI content without human input. Educational AI-assisted content with genuine human direction and disclosure is considered acceptable. Original animation plus light human direction (Section 2.5) is the protection.
- Shorts pay little per view; sponsorships or long-form follow-ups are more lucrative. **Treat money as a bonus.**

---

## 18. Resume angle

The highlights are the hard engineering, not "automated YouTube":

- An LLM code-generation pipeline with **static validation and a self-repair loop**
- A **sandboxed execution service** for untrusted, AI-generated code (container isolation, timeouts, resource limits)
- **Multi-model orchestration** with explicit JSON contracts
- **Audio-visual synchronization** using TTS word timestamps
- **Reliability design:** a queue buffer, retries, fallback providers, and alerts

Track these metrics from day one (the harness writes `summary.json`; the n8n runs write logs):

- First-try render success rate, and success after repairs
- Average repair attempts
- A model comparison (for example Gemini Flash vs Pro vs Llama on the same 30 topics)
- Consecutive days published, and total videos
- Cost per video

Make the repo public with a README, an architecture diagram, a channel link and the metrics. Example bullet (the numbers are placeholders):

> Built an automated pipeline publishing daily animated STEM explainers; designed a sandboxed Manim render service and an LLM self-repair loop that raised render success from X% to Y%, shipping N consecutive daily videos at under $Z per video.

---

## 19. Working style (for Claude Code)

- **The owner is learning Docker and infrastructure as he goes.** Explain *why* briefly when introducing something new, such as what PyTorch is for or what a render service is.
- **Give only the changes needed.** The owner prefers targeted edits: which file, which function, what to replace. Avoid rewriting whole files unless necessary. If a whole-function replacement is clearer, say exactly where it starts and ends, and warn about indentation.
- **Commands run in the Ubuntu terminal** under `~/shorts-pipeline`. Never assume PowerShell.
- Work **step by step and test after each change.** Use the readiness wait on `/health` after rebuilds.
- When something fails, ask for the **exact output** (`docker compose logs <service> --tail 40`) rather than guessing. When a guess is the most likely cause, say so and say how to confirm it.
- **Ask at most one question at a time.**
- **Never expose secrets.** If the owner pastes a key, tell him to rotate it.
- The owner has strong opinions and moves fast. Flag risks (policy, terms, cost) plainly, then respect his decision.

---

## 20. Files to create at handover

### `CLAUDE.md` (project root)

```markdown
# STEM Shorts Pipeline

Read docs/HANDOVER.md fully before starting. It holds all decisions, current
file contents, gotchas, and the plan for Phases 4 to 9. Current phase: 4 (prompts).

Rules:
- The files on disk are the source of truth; if they differ from the handover,
  show the diff and ask before overwriting.
- Give targeted edits, not whole-file rewrites, unless asked.
- All commands run in the Ubuntu (WSL2) terminal in ~/shorts-pipeline.
- After rebuilding containers, wait for /health before testing.
- Never print or commit secrets (.env).
```

### `.gitignore`

```
.env
.venv/
data/
__pycache__/
*.pyc
```

### First prompt to give Claude Code

> Read CLAUDE.md and docs/HANDOVER.md. Then walk me through the open items in Section 10, one at a time, starting with the n8n encryption key check. After that we start Phase 4.
