# Local Development

## Prerequisites

- Docker (this repo was developed against OrbStack) — the server runs **only** in Docker
- `uv` — dependency management, tests, lint, and the host MLX audio server
- Apple Silicon Mac for the recommended MLX STT/TTS servers
- `hf` (Hugging Face CLI) — optional model pulls; MLX models use the HF cache
- Xcode 26+ with an iOS simulator (iOS app)
- Android SDK + an emulator image (Android app)

## Server

```bash
cp backend/.env.example backend/.env     # defaults to the MLX providers
make audio-server                        # terminal 1: STT/TTS on the Mac (127.0.0.1:8000)
make up                                  # terminal 2: build image + start server
open http://localhost:7860/client        # talk through the browser
```

`make audio-server` runs `mlx_audio.server` natively (Metal/MLX). The first
request per model downloads and loads it; after that models stay warm. It is
bound to loopback only — the Docker backend reaches it through
`host.docker.internal`, and phones cannot connect to it.

If you prefer everything in-container (no host server), set
`STT_PROVIDER=moonshine` and `TTS_PROVIDER=kokoro` in `backend/.env` and skip
`make audio-server`.

Useful targets:

```bash
make logs        # follow logs
make restart     # after editing backend/.env
make down        # stop
make test        # backend unit tests (host uv)
make lint        # ruff
EXTRAS="whisper piper cloud" make build   # optional providers
```

## Apps

**Android**

```bash
cd frontend/mai-voice-android
./gradlew :app:assembleDebug
# or open in Android Studio and Run
```

Default server URL: `http://10.0.2.2:7860` (emulator → host). Change it in the
app's Settings screen for physical devices (use your Mac's LAN IP).

**iOS**

```bash
cd frontend/mai-voice-ios
xcodebuild -project mai-voice-ios.xcodeproj -scheme mai-voice-ios \
  -destination 'platform=iOS Simulator,name=iPhone 17' build
# or open in Xcode and Run
```

Default server URL: `http://localhost:7860` (simulator shares the host network).
`--auto-connect` as a launch argument connects immediately (useful for testing).

For physical devices add a local network permission prompt on first connect
(already configured via `Info.plist`), and point Settings at the Mac's LAN IP.

## Hitting the server without a mic

```bash
curl http://localhost:7860/status          # {"status":"ready",...}
docker compose logs -f backend             # watch sessions, transcripts, TTS
```

The development runner also serves a prebuilt browser client at `/client/`.

## Troubleshooting

- **No sound in browser client** — the runner logs `on_client_connected`; check
  `make logs` for transcription and TTS lines.
- **Android can't reach the server** — emulator must use `10.0.2.2`, not
  `localhost`. Check the Settings screen value.
- **iOS HTTP blocked** — `Info.plist` sets `NSAllowsLocalNetworking`; keep the
  server on plain HTTP only for dev.
- **First session is slow** — Moonshine/Kokoro load per session
  (`MODEL_LIFECYCLE=session`). Run `make models` first so nothing downloads
  mid-session, or set `MODEL_LIFECYCLE=warm` while iterating.
- **Qwen is slow** — CPU inference is seconds per sentence; see
  `docs/providers.md`.
- **No bot audio with `*_PROVIDER=mlx`** — is `make audio-server` running? Check
  `curl http://127.0.0.1:8000/` on the Mac, and
  `docker compose exec backend curl -s http://host.docker.internal:8000/`.
- **`make audio-server` not reachable from the phone** — that is by design. The
  MLX server is loopback-only; only the Pipecat server (port 7860) is exposed.
