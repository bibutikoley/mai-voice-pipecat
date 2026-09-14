FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    HF_HOME=/root/.cache/huggingface

WORKDIR /app

# espeak-ng: Kokoro phonemizer. libsndfile1/sox/libgomp1: local model audio + ONNX.
RUN apt-get update && apt-get install -y --no-install-recommends \
        espeak-ng libsndfile1 sox libgomp1 tini curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first for layer caching. EXTRAS is a space-separated list of
# optional extras (whisper, piper, cloud) to install alongside the defaults.
COPY pyproject.toml uv.lock ./
ARG EXTRAS=""
RUN --mount=type=cache,target=/root/.cache/uv \
    sh -c 'set -e; opts=""; for e in $EXTRAS; do opts="$opts --extra $e"; done; uv sync --frozen --no-dev $opts'

COPY bot.py ./
COPY mai_voice ./mai_voice

EXPOSE 7860

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://localhost:7860/status || exit 1

ENTRYPOINT ["/usr/bin/tini", "-e", "143", "--"]
CMD ["python", "bot.py", "--host", "0.0.0.0", "--port", "7860"]
