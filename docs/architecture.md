# Architecture

```
┌─────────────┐        ┌─────────────┐
│  iOS app    │        │ Android app │
│  SwiftUI    │        │  Compose    │
└──────┬──────┘        └──────┬──────┘
       └───────────┬───────────┘
                   │ SmallWebRTC (audio + RTVI)
                   │ POST /start → /sessions/{id}/api/offer
          ┌────────▼─────────┐
          │ Docker: backend  │
          │ Pipecat runner   │
          │ :7860            │
          └──┬────────────┬──┘
             │            │
   STT :8001 │            │ LLM over HTTPS (any OpenAI-compatible endpoint
   TTS :8002 │            │ or Sarvam; e.g. Ollama Cloud gpt-oss:120b)
             │            │
   ┌─────────▼────────┐   │
   │ Mac (Metal/MLX)  │   │
   │ stt-server :8001 │   │
   │ tts-server :8002 │   │
   └──────────────────┘   ▼
                    LLM endpoint (cloud or host)
```

**Trust boundary**: the MLX audio servers bind to `127.0.0.1` only. The Docker
backend reaches them through `host.docker.internal`; phones on the LAN cannot
connect to them at all. Only the Pipecat server (port 7860) is exposed to
clients. Verified: LAN IP → connection refused, container → 200.

STT and TTS run as separate processes (`make stt-server`, `make tts-server`) so
either can be changed or restarted without touching the other or the Docker
server.

## Components

| Piece | Location | Role |
|---|---|---|
| Pipecat server | `backend/` | Development runner (FastAPI + uvicorn) that starts one pipeline per session |
| Providers | `backend/mai_voice/providers/` | Env-selected STT/TTS/LLM services behind a small registry |
| MLX audio servers | Mac host (`make stt-server`, `make tts-server`) | STT/TTS inference natively on Apple Silicon; loopback-only, separate processes |
| Lifecycle | `backend/mai_voice/lifecycle.py` | Per-session model release + allocator trim (in-container providers) |
| Docker | `backend/Dockerfile`, `docker-compose.yml` | The only supported way to run the server |
| Android client | `frontend/mai-voice-android/` | Compose UI + `ai.pipecat:client` SmallWebRTC transport |
| iOS client | `frontend/mai-voice-ios/` | SwiftUI UI + `PipecatClientIOS` + SmallWebRTC transport |

## Session flow

1. App `POST /start` with `{"transport": "webrtc"}` to the runner.
2. Runner creates a session id and returns it (`SmallWebRTCStartBotResult`).
3. SDK asks the transport for connection params; the transport rewrites the
   endpoint to `/sessions/{id}/api/offer` and posts the SDP offer.
4. Runner instantiates a `SmallWebRTCConnection` and calls `bot()` in a
   background task; the pipeline is built per session.
5. On connect: system prompt + greeting developer message + `LLMRunFrame` →
   greeting.
6. Audio flows over WebRTC. With `STT_PROVIDER=mlx` / `TTS_PROVIDER=mlx`, the
   container calls the Mac's STT server (`:8001`) and TTS server (`:8002`) over
   HTTP; models stay warm there and never enter the container's memory.
7. On disconnect: `task.cancel()` → each service `cleanup()`. In-container
   providers release their model and `malloc_trim(0)` returns heap pages to the
   OS; MLX providers hold no models, so there is nothing to release.

## HTTP surface (port 7860)

| Route | Purpose |
|---|---|
| `POST /start` | Session start (used by both apps) |
| `POST /api/offer`, `PATCH /api/offer` | Direct SDP offer / ICE candidates |
| `/sessions/{id}/api/offer` | Offer via session proxy (what the SDKs use after `/start`) |
| `/client/` | Prebuilt browser client for quick manual tests |
| `GET /status` | Readiness probe (Docker healthcheck) |

## Ports

| Port | Service | Reachable from |
|---|---|---|
| 7860 | Pipecat server (`/start`, `/client`, `/status`) | apps and LAN |
| 8001 | MLX STT server (`make stt-server`) | loopback + Docker via `host.docker.internal` |
| 8002 | MLX TTS server (`make tts-server`) | loopback + Docker via `host.docker.internal` |

## Model storage

Models are not baked into the image.

In-container providers read from default host caches that are mounted in:

| Model | Host cache | Container path |
|---|---|---|
| Kokoro | `~/.cache/pipecat/kokoro-onnx` | `/root/.cache/pipecat` |
| Moonshine | `~/Library/Caches/moonshine_voice` | `/root/.cache/moonshine_voice` |
| Qwen / HF models | `~/.cache/huggingface` | `/root/.cache/huggingface` |

MLX models (`mlx-community/...`) download to `~/.cache/huggingface` on the host
and are loaded by the STT/TTS server processes — they are never visible to the
container.

## Memory lifecycle

This applies to in-container providers (Moonshine, Kokoro, Qwen, Whisper,
Piper). Services are built inside the session function, so each session owns its
models. `ReleasesModels.cleanup()` (mixed into every in-container provider) drops
the model reference on disconnect and calls `release_memory()`: `gc.collect()`
plus `malloc_trim(0)` on glibc, and torch allocator caches only if torch is
already loaded. Verified with Moonshine + Kokoro: a session peaks around 1.2 GB
and returns to ~300 MB after disconnect; consecutive sessions reuse the same
footprint. `docker compose down`/`stop` frees everything.

`MODEL_LIFECYCLE=warm` skips the per-session release (models are then reclaimed
on process exit only).

MLX providers hold no models in the container, so there is nothing to release;
their models live in the host server processes until `make stt-stop` /
`make tts-stop`.
