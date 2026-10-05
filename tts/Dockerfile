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