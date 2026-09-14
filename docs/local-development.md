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
make stt-server                          # terminal 1: STT server (127.0.0.1:8001)
make tts-server                          # terminal 2: TTS server (127.0.0.1:8002)
make up                                  # terminal 3: Docker Pipecat server (:7860)
open http://localhost:7860/client        # talk through the browser
```

The two host servers are independent processes: changing or restarting one
(`make stt-stop` / `make tts-stop`, then the matching start) never affects the
other or the Docker server. They run `mlx_audio.server` natively (Metal/MLX); the
first request per model downloads and loads it, after which models stay warm.
Both bind to loopback only — the Docker backend reaches them through
`host.docker.internal`, and phones cannot connect to them.

Stop each server independently:

```bash
make stt-stop    # stop only the STT server
make tts-stop    # stop only the TTS server
make down        # stop the Docker Pipecat server
```

If you prefer everything in-container (no host servers), set
`STT_PROVIDER=moonshine` and `TTS_PROVIDER=kokoro` in `backend/.env` and skip the
two host-server commands.

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
- **First session is slow (in-container providers)** — Moonshine/Kokoro/Qwen
  load per session (`MODEL_LIFECYCLE=session`). Run `make models` first so
  nothing downloads mid-session. MLX providers are unaffected: their models load
  in the host servers and stay warm.
- **Qwen is slow** — CPU inference is seconds per sentence; see
  `docs/providers.md`.
- **No bot audio with `*_PROVIDER=mlx`** — are the host servers running? Check
  `curl http://127.0.0.1:8001/` (STT) and `curl http://127.0.0.1:8002/` (TTS) on
  the Mac, and from the container:
  `docker compose exec backend curl -s http://host.docker.internal:8001/`.
- **`make stt-server` / `make tts-server` not reachable from the phone** — that
  is by design. They are loopback-only; only the Pipecat server (port 7860) is
  exposed.
