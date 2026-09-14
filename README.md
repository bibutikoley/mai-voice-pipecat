# mai-voice-pipecat

Voice AI monorepo: a Dockerized [Pipecat](https://pipecat.ai) server with native
Android and iOS clients.

- **Server**: SmallWebRTC transport, Silero VAD, swappable local (Moonshine /
  Kokoro / Qwen) or cloud (Deepgram / Cartesia) STT + TTS, any
  OpenAI-compatible LLM. Runs only in Docker.
- **Clients**: `frontend/mai-voice-android` (Compose) and
  `frontend/mai-voice-ios` (SwiftUI), both using the Pipecat client SDKs.

## Quickstart

```bash
cp backend/.env.example backend/.env     # defaults need no API keys
make models                              # warm Moonshine + Kokoro caches (one time)
make up                                  # build and start the server
open http://localhost:7860/client        # browser voice client
```

Talk to the bot in the browser, then point the apps at the server:

- Android emulator: `http://10.0.2.2:7860`
- iOS simulator: `http://localhost:7860`
- Physical devices: your Mac's LAN IP (set in each app's settings screen)

## Switching providers

Edit `backend/.env` and `make restart`. STT and TTS are independent:

```env
STT_PROVIDER=moonshine   # moonshine | whisper | qwen | deepgram
TTS_PROVIDER=kokoro      # kokoro | piper | qwen | cartesia
LLM_MODE=stub            # stub | openai_compatible
```

Qwen (ASR and/or TTS) works out of the box with the models in your Hugging Face
cache. Whisper/Piper/cloud providers need an image built with extras:

```bash
EXTRAS="whisper piper cloud" make build
```

## LLM

`LLM_MODE=stub` replies with canned text so you can test the full voice loop
without keys. To use your endpoint:

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://your-endpoint/v1
LLM_API_KEY=...
LLM_MODEL=...
```

From Docker, a server running on the host (Ollama, LM Studio, vLLM) is reachable
at `http://host.docker.internal:<port>`.

## Models and memory

Models stay in their default host caches and are mounted into the container; no
model is baked into the image. With `MODEL_LIFECYCLE=session` (default), a
session's models are released as soon as it disconnects, and `docker compose
down` frees everything.

## Docs

- [`docs/plan.md`](docs/plan.md) — build plan and decisions
- `docs/architecture.md`, `docs/local-development.md`, `docs/providers.md`,
  `docs/sdk-notes.md`

## Layout

```
backend/     Pipecat server (Python 3.12, uv, Docker)
frontend/    Native Android + iOS apps
docs/        Architecture and guides
```
