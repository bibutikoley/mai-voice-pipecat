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
              └────────┬─────────┘
                       │
   Silero VAD → STT (Moonshine/Qwen/Whisper/Deepgram)
                       │
        LLM (stub | any OpenAI-compatible endpoint)
                       │
     TTS (Kokoro/Qwen/Piper/Cartesia) → transport out
```

## Components

| Piece | Location | Role |
|---|---|---|
| Pipecat server | `backend/` | Development runner (FastAPI + uvicorn) that starts one pipeline per session |
| Providers | `backend/mai_voice/providers/` | Env-selected STT/TTS/LLM services behind a small registry |
| Lifecycle | `backend/mai_voice/lifecycle.py` | Per-session model release + allocator trim |
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
6. Audio flows over WebRTC; RTVI events carry transcripts, speaking state, and
   audio levels back to the app.
7. On disconnect: `task.cancel()` → each service `cleanup()` releases its model
   and `malloc_trim(0)` returns heap pages to the OS.

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
