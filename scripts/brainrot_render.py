"""Brainrot renderer: script text -> am_adam TTS -> word-accurate ASS captions
-> ffmpeg composite over a random gameplay slice.

Caption guarantee: the words shown are the script text itself (display ground
truth). TTS word timestamps only provide timing; any script word the matcher
can't pair with a TTS token gets its time interpolated between matched
neighbours. A word can therefore never be missing from screen.

ffmpeg runs inside the renderer container (has libass). Host paths data/...
map to /files/... in the container; assets/ maps to /assets/.
"""
import base64
import difflib
import json
import random
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TTS_URL = "http://localhost:8001/speak"
VOICE = "am_adam"
GAMEPLAY_DIR = ROOT / "assets" / "gameplay"

# caption chunking: a chunk is what's on screen at once
MAX_CHUNK_CHARS = 13
MAX_CHUNK_WORDS = 3

ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Brain,Archivo Black,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,6,2,5,20,20,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def tts(text):
    body = json.dumps({"text": text, "voice": VOICE}).encode()
    req = urllib.request.Request(TTS_URL, data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return base64.b64decode(r["audio_b64"]), r["words"], r["duration"]


def _norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def align(script_text, tts_words):
    """Pair every script word with a (start, end) time. Returns
    [(word, start, end)] covering EVERY script word."""
    script_words = script_text.split()
    a = [_norm(w) for w in script_words]
    b = [_norm(t["w"]) for t in tts_words]
    times = [None] * len(script_words)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for block in sm.get_matching_blocks():
        for k in range(block.size):
            t = tts_words[block.b + k]
            times[block.a + k] = (t["s"], t["e"])
    # interpolate the unmatched (TTS expanded "128" -> three tokens, etc.)
    for i, tm in enumerate(times):
        if tm is not None:
            continue
        prev_e = next((times[j][1] for j in range(i - 1, -1, -1)
                       if times[j] is not None), 0.0)
        nxt_s = next((times[j][0] for j in range(i + 1, len(times))
                      if times[j] is not None), prev_e + 0.4)
        # count the gap's unmatched words and split the span evenly
        gap_lo = i
        while gap_lo > 0 and times[gap_lo - 1] is None:
            gap_lo -= 1
        gap_hi = i
        while gap_hi + 1 < len(times) and times[gap_hi + 1] is None:
            gap_hi += 1
        n = gap_hi - gap_lo + 1
        span = max(nxt_s - prev_e, 0.12 * n)
        k = i - gap_lo
        times[i] = (prev_e + span * k / n, prev_e + span * (k + 1) / n)
    return [(w, s, e) for w, (s, e) in zip(script_words, times)]


def chunk(aligned):
    """Group aligned words into screen chunks (<=3 words, <=13 chars)."""
    chunks, cur = [], []
    for w, s, e in aligned:
        cand_len = len(" ".join([c[0] for c in cur] + [w]))
        if cur and (len(cur) >= MAX_CHUNK_WORDS or cand_len > MAX_CHUNK_CHARS):
            chunks.append(cur)
            cur = []
        cur.append((w, s, e))
        if w[-1:] in ".!?,;:":  # break at clause ends
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def _ts(t):
    t = max(t, 0)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02}:{s:05.2f}"


def build_ass(chunks, total):
    lines = [ASS_HEADER]
    for i, ch in enumerate(chunks):
        text = " ".join(w for w, _, _ in ch).upper()
        text = re.sub(r"[{}\\]", "", text)
        start = ch[0][1]
        end = chunks[i + 1][0][1] if i + 1 < len(chunks) else min(ch[-1][2] + 0.6, total)
        if end - start < 0.15:
            end = start + 0.15
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Brain,,0,0,0,,"
                     f"{{\\fad(60,0)}}{text}")
    return "\n".join(lines) + "\n"


def _exec(args):
    proc = subprocess.run(["docker", "compose", "exec", "-T", "renderer"] + args,
                          capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        raise RuntimeError(f"{args[0]} failed: {proc.stderr[-400:]}")
    return proc.stdout


def pick_gameplay(need_s, seed=None):
    rng = random.Random(seed)
    clips = sorted(GAMEPLAY_DIR.glob("*.mp4"))
    if not clips:
        raise RuntimeError("no gameplay clips in assets/gameplay/")
    clip = rng.choice(clips)
    dur = float(_exec(["ffprobe", "-v", "error", "-show_entries",
                       "format=duration", "-of", "csv=p=0",
                       f"/assets/gameplay/{clip.name}"]).strip())
    margin = 2.0
    max_start = max(dur - need_s - margin, margin)
    start = rng.uniform(margin, max_start)
    return clip.name, round(start, 2)


def render(script_text, job_id, seed=None):
    out_host = ROOT / "data" / "brainrot" / job_id
    out_host.mkdir(parents=True, exist_ok=True)
    out_ct = f"/files/brainrot/{job_id}"

    wav, words, duration = tts(script_text)
    (out_host / "voice.wav").write_bytes(wav)
    aligned = align(script_text, words)
    chunks = chunk(aligned)
    (out_host / "caps.ass").write_text(build_ass(chunks, duration),
                                       encoding="utf-8")

    total = duration + 0.7  # breathing room after the last word
    clip_name, start = pick_gameplay(total, seed=seed)
    vf = ("crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',scale=720:1280,setsar=1,"
          f"fps=30,ass={out_ct}/caps.ass:fontsdir=/assets/fonts")
    _exec(["ffmpeg", "-y", "-v", "error",
           "-ss", str(start), "-t", f"{total:.2f}",
           "-i", f"/assets/gameplay/{clip_name}",
           "-i", f"{out_ct}/voice.wav",
           "-filter:v", vf,
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "22",
           "-c:a", "aac", "-b:a", "128k",
           "-t", f"{total:.2f}", "-movflags", "+faststart",
           f"{out_ct}/final.mp4"])
    return {"ok": True, "duration": round(total, 2), "clip": clip_name,
            "clip_start": start, "words": len(aligned), "chunks": len(chunks),
            "path": str(out_host / "final.mp4")}


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "Testing one two three. Every single word must appear on screen, "
        "including numbers like 128 and acronyms like API and GPU. "
        "No word gets skipped. Ever.")
    print(json.dumps(render(text, "brtest", seed=7), indent=2))
