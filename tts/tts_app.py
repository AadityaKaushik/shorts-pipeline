import base64, io, os

import numpy as np
import soundfile as sf
from fastapi import FastAPI
from fastapi.responses import Response
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