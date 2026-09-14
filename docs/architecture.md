# Architecture

```
┌─────────────┐        ┌─────────────┐
│  iOS app    │        │ Android app │
│  SwiftUI    │        │  Compose    │
└──────┬──────┘        └──────┬──────┘
       │   SmallWebRTC (audio + RTVI)   │
       └───────────────┬───────────────┘
                       │  POST /start → /api/offer
              ┌────────▼─────────┐
              │  Docker: backend │
              │  Pipecat runner  │
              │  :7860           │
              └───┬──────────┬───┘
                  │          │
   STT/TTS over HTTP          │  LLM over HTTPS
   host.docker.internal:8000  │  ollama.com
                  │          │
        ┌─────────▼────────┐ │
        │ Mac (Metal/MLX)  │ │
        │ mlx_audio.server │ │
        │ 127.0.0.1:8000   │ │
        └──────────────────┘ │
                             ▼
                    gpt-oss:120b (cloud)
```

**Trust boundary**: the MLX audio server binds to `127.0.0.1` only. The Docker
backend reaches it through `host.docker.internal`; phones on the LAN cannot
connect to it at all. Only the Pipecat server (port 7860) is exposed to clients.
Verified: LAN IP → connection refused, container → 200.

## Components

| Piece | Location | Role |
|---|---|---|
| Pipecat server | `backend/` | Development runner (FastAPI + uvicorn) that starts one pipeline per session |
| Providers | `backend/mai_voice/providers/` | Env-selected STT/TTS/LLM services behind a small registry |
| MLX audio servers | Mac host (`make audio-server`) | STT/TTS inference natively on Apple Silicon; loopback-only, reached by the container |
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
5. On connect: developer prompt + `LLMRunFrame` → greeting.
6. Audio flows over WebRTC. With `STT_PROVIDER=mlx` / `TTS_PROVIDER=mlx`, the
   container calls the Mac's MLX server over HTTP (`host.docker.internal:8000`);
   models stay warm there and never enter the container's memory.
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

## Model storage

Models are not baked into the image. Default host caches are mounted:

| Model | Host cache | Container path |
|---|---|---|
| Kokoro | `~/.cache/pipecat/kokoro-onnx` | `/root/.cache/pipecat` |
| Moonshine | `~/Library/Caches/moonshine_voice` | `/root/.cache/moonshine_voice` |
| Qwen / HF models | `~/.cache/huggingface` | `/root/.cache/huggingface` |

MLX models (`mlx-community/...`) download to `~/.cache/huggingface` on the host
and are loaded by the host server, not by the container.

## Memory lifecycle

Services are built inside the session function, so each session owns its
models. `ReleasesModels.cleanup()` (mixed into every local provider) drops the
model reference on disconnect and calls `release_memory()`: `gc.collect()` plus
`malloc_trim(0)` on glibc, and torch allocator caches only if torch is already
loaded. Verified: a session peaks around 1.2 GB and returns to ~300 MB after
disconnect; consecutive sessions reuse the same footprint. `docker compose
down`/`stop` frees everything.

`MODEL_LIFECYCLE=warm` skips the per-session release (models are then reclaimed
on process exit only).
