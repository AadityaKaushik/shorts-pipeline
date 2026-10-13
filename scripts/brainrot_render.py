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
import os
import random
import re
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TTS_URL = "http://localhost:8001/speak"
VOICE = "am_adam"
GAMEPLAY_DIR = ROOT / "assets" / "gameplay"
MASCOT_DIR = ROOT / "assets" / "mascot_trevor"

# Pose order = narrative order: hook, intro, body x3, subscribe+kicker.
# Matched by filename substring, so the files can be renamed freely otherwise.
POSES = ["Shrugging", "Waving", "Pointing", "Idea", "Thoughtful", "Thumbs-Up"]
# Mascot: 55% of frame height, bottom-left. Source PNGs carry ~18% transparent
# margin on the left, hence the negative x. Captions are top-anchored at
# CAPTION_TOP (text spans ~420-500); the mascot's hair starts ~10px below
# MASCOT_Y (~597), so they never touch.
MASCOT_H = 704
MASCOT_X = -60
MASCOT_Y = 1280 - MASCOT_H + 10
CAPTION_TOP = 420

# The account handle: spoken as words, captioned as the exact searchable handle.
HANDLE_SPOKEN = "Daily Trevor dot AI"
HANDLE_SHOWN = "@daily_trevor.ai"
POP_PX, POP_S = 60, 0.18
BOB_PX, BOB_HZ = 4, 1.4

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
Style: Brain,Archivo Black,68,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,6,2,8,20,20,{caption_top},1

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


def show_handle(aligned):
    """Merge the spoken handle words into one caption word showing the real handle."""
    spoken = [_norm(w) for w in HANDLE_SPOKEN.split()]
    n, out, i = len(spoken), [], 0
    while i < len(aligned):
        window = aligned[i:i + n]
        if len(window) == n and [_norm(w) for w, _, _ in window] == spoken:
            tail = re.sub(r"^.*?([.!?,]*)$", r"\1", window[-1][0])
            out.append((HANDLE_SHOWN + tail, window[0][1], window[-1][2]))
            i += n
        else:
            out.append(aligned[i])
            i += 1
    return out


def build_ass(chunks, total):
    lines = [ASS_HEADER.replace("{caption_top}", str(CAPTION_TOP))]
    for i, ch in enumerate(chunks):
        text = " ".join(w for w, _, _ in ch).upper()
        text = re.sub(r"[{}\\]", "", text)
        start = ch[0][1]
        end = chunks[i + 1][0][1] if i + 1 < len(chunks) else min(ch[-1][2] + 0.6, total)
        if end - start < 0.15:
            end = start + 0.15
        # chunks are capped at MAX_CHUNK_CHARS, except a single long word (the
        # handle, a URL) — shrink those so a no-wrap line never runs off-frame
        size = "" if len(text) <= MAX_CHUNK_CHARS else f"\\fs{68 * MAX_CHUNK_CHARS // len(text)}"
        lines.append(f"Dialogue: 0,{_ts(start)},{_ts(end)},Brain,,0,0,0,,"
                     f"{{\\fad(60,0){size}}}{text}")
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


def _shared_dir(path):
    """Host-created dirs must be writable by the container's (different) uid."""
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o777)
    return path


def prepare_mascot():
    """Scale the six poses once to MASCOT_H; returns container paths in POSES order."""
    _shared_dir(ROOT / "data" / "brainrot" / "_mascot")
    out = []
    for i, key in enumerate(POSES):
        matches = [p for p in MASCOT_DIR.glob("*.png") if key.lower() in p.name.lower()]
        if len(matches) != 1:
            raise RuntimeError(f"mascot pose {key!r}: expected 1 file, found {len(matches)}")
        dst_host = ROOT / "data" / "brainrot" / "_mascot" / f"pose{i}_{MASCOT_H}.png"
        dst_ct = f"/files/brainrot/_mascot/pose{i}_{MASCOT_H}.png"
        if not dst_host.exists():
            _exec(["ffmpeg", "-y", "-v", "error", "-i", f"/assets/mascot_trevor/{matches[0].name}",
                   "-vf", f"scale=-1:{MASCOT_H}:flags=lanczos", dst_ct])
        out.append(dst_ct)
    return out


def _split_body(words, n_parts=3):
    """Split a word list into n parts, snapping cuts to nearby sentence ends."""
    n = len(words)
    cuts = []
    for k in range(1, n_parts):
        target = round(n * k / n_parts)
        ends = [i + 1 for i, w in enumerate(words) if w[-1:] in ".!?" and 0 < i + 1 < n]
        near = [e for e in ends if abs(e - target) <= 6 and (not cuts or e - cuts[-1] >= 3)]
        cuts.append(min(near, key=lambda e: abs(e - target)) if near else target)
    return cuts


def pose_schedule(aligned, sections, total):
    """[(pose_index, start, end)] — one pose per narrative beat, all six in order.

    sections: [("hook", n), ("intro", n), ("body", n), ("cta", n), ("kicker", n)]
    word counts that sum to len(aligned). Without sections, six equal slices."""
    if not sections:
        starts = [total * i / 6 for i in range(6)]
    else:
        idx, first = 0, {}
        for name, n in sections:
            first[name] = idx
            idx += n
        b0, bn = first["body"], dict(sections)["body"]
        body_words = [w for w, _, _ in aligned[b0:b0 + bn]]
        c1, c2 = _split_body(body_words)
        word_starts = [first["hook"], first["intro"], b0, b0 + c1, b0 + c2, first["cta"]]
        starts = [0.0] + [aligned[i][1] for i in word_starts[1:]]
    ends = starts[1:] + [total]
    return [(i, s, e) for i, (s, e) in enumerate(zip(starts, ends))]


def render(script_text, job_id, seed=None, sections=None):
    out_host = _shared_dir(ROOT / "data" / "brainrot" / job_id)
    out_ct = f"/files/brainrot/{job_id}"

    wav, words, duration = tts(script_text)
    (out_host / "voice.wav").write_bytes(wav)
    aligned = align(script_text, words)
    chunks = chunk(show_handle(aligned))
    (out_host / "caps.ass").write_text(build_ass(chunks, duration),
                                       encoding="utf-8")

    total = duration + 0.7  # breathing room after the last word
    clip_name, start = pick_gameplay(total, seed=seed)
    poses = prepare_mascot()
    schedule = pose_schedule(aligned, sections, total)

    inputs = ["-ss", str(start), "-t", f"{total:.2f}",
              "-i", f"/assets/gameplay/{clip_name}",
              "-i", f"{out_ct}/voice.wav"]
    for p in poses:
        inputs += ["-framerate", "30", "-loop", "1", "-i", p]

    graph = [("[0:v]crop='min(iw,ih*9/16)':'min(ih,iw*16/9)',"
              "scale=720:1280,setsar=1,fps=30[v0]")]
    for k, (i, s, e) in enumerate(schedule):
        # pop: start POP_PX lower and ease up over POP_S; bob: gentle sway
        y = (f"{MASCOT_Y}+{BOB_PX}*sin(2*PI*{BOB_HZ}*t)"
             f"+{POP_PX}*pow(max(0\\,1-(t-{s:.3f})/{POP_S})\\,2)")
        graph.append(f"[v{k}][{i + 2}:v]overlay=x={MASCOT_X}:y='{y}'"
                     f":enable='between(t\\,{s:.3f}\\,{e:.3f})'[v{k + 1}]")
    graph.append(f"[v{len(schedule)}]ass={out_ct}/caps.ass:fontsdir=/assets/fonts[out]")

    _exec(["ffmpeg", "-y", "-v", "error", *inputs,
           "-filter_complex", ";".join(graph),
           "-map", "[out]", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "22",
           # Instagram wants 44.1/48 kHz stereo; Kokoro emits 24 kHz mono
           "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
           "-t", f"{total:.2f}", "-movflags", "+faststart",
           f"{out_ct}/final.mp4"])
    for i, s, e in schedule:  # one still per pose, mid-pose, for review
        _exec(["ffmpeg", "-y", "-v", "error", "-ss", f"{(s + e) / 2:.2f}",
               "-i", f"{out_ct}/final.mp4", "-frames:v", "1", "-q:v", "4",
               f"{out_ct}/preview_{i}.jpg"])
    return {"ok": True, "duration": round(total, 2), "clip": clip_name,
            "clip_start": start, "words": len(aligned), "chunks": len(chunks),
            "poses": [(POSES[i], round(s, 2)) for i, s, _ in schedule],
            "path": str(out_host / "final.mp4")}


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else (
        "Testing one two three. Every single word must appear on screen, "
        "including numbers like 128 and acronyms like API and GPU. "
        "No word gets skipped. Ever.")
    print(json.dumps(render(text, "brtest", seed=7), indent=2))
