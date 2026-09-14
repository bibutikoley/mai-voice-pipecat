# mai-voice-pipecat

Voice AI monorepo: a Dockerized [Pipecat](https://pipecat.ai) server with native
Android and iOS clients.

- **Server**: SmallWebRTC transport, Silero VAD, swappable STT + TTS — MLX
  (Apple Silicon, host servers), local in-container (Moonshine / Kokoro / Qwen),
  or cloud (Deepgram / Cartesia / Sarvam) — and an OpenAI-compatible or Sarvam
  LLM. The Pipecat server runs only in Docker; STT/TTS can run natively on the
  Mac behind loopback-only HTTP servers.
- **Clients**: `frontend/mai-voice-android` (Compose) and
  `frontend/mai-voice-ios` (SwiftUI), both using the Pipecat client SDKs.

## Quickstart

```bash
cp backend/.env.example backend/.env     # defaults to the MLX (Apple Silicon) providers
make stt-server                          # terminal 1: STT server (127.0.0.1:8001)
make tts-server                          # terminal 2: TTS server (127.0.0.1:8002)
make up                                  # terminal 3: Docker Pipecat server (:7860)
open http://localhost:7860/client        # browser voice client
```

Talk to the bot in the browser, then point the apps at the server:

- Android emulator: `http://10.0.2.2:7860`
- iOS simulator: `http://localhost:7860`
- Physical devices: your Mac's LAN IP (set in each app's settings screen)

Stop them independently: `make stt-stop`, `make tts-stop`, `make down`.

## Switching providers

Edit `backend/.env` and `make restart`. STT and TTS are independent:

```env
STT_PROVIDER=mlx         # mlx | moonshine | whisper | qwen | deepgram | sarvam
TTS_PROVIDER=mlx         # mlx | kokoro | piper | qwen | cartesia | sarvam
LLM_MODE=stub            # stub | openai_compatible | sarvam
```

`mlx` runs STT/TTS natively on the Mac via `make stt-server` / `make tts-server`
(Metal/MLX) and is loopback-only. `sarvam` adds Indic-language cloud
STT/TTS/LLM (built into the default image). The other providers run inside the
container. Qwen works out of the box with the models in your Hugging Face cache;
Whisper/Piper/cloud providers need an image built with extras:

```bash
EXTRAS="whisper piper cloud" make build
```

## LLM

`LLM_MODE=stub` replies with canned text so you can test the full voice loop
without keys. To use your endpoint (e.g. Ollama Cloud at
`https://ollama.com/v1`):

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://ollama.com/v1
LLM_API_KEY=...
LLM_MODEL=...
```

From Docker, a server running on the host (Ollama, LM Studio, vLLM) is reachable
at `http://host.docker.internal:<port>`.

`LLM_MODE=sarvam` uses Sarvam's LLM (see `docs/providers.md`).

## Models and memory

In-container providers (Moonshine, Kokoro, Qwen, Whisper, Piper) read their
models from default host caches mounted into the container; no model is baked
into the image. With `MODEL_LIFECYCLE=session` (default), their models are
released as soon as a session disconnects, and `docker compose down` frees
everything.

MLX models live in the host's Hugging Face cache and are loaded by the STT/TTS
server processes — they never enter the container. `make stt-stop`,
`make tts-stop`, and `make down` free them.

## Docs

- [`docs/plan.md`](docs/plan.md) — build plan, decisions, and implementation status
- [`docs/architecture.md`](docs/architecture.md) — components, session flow, ports, model storage
- [`docs/local-development.md`](docs/local-development.md) — running everything locally
- [`docs/providers.md`](docs/providers.md) — every STT/TTS/LLM provider and switching
- [`docs/sdk-notes.md`](docs/sdk-notes.md) — Android/iOS SDK integration notes

## Layout

```
backend/     Pipecat server (Python 3.12, uv, Docker)
frontend/    Native Android + iOS apps
docs/        Architecture and guides
```
