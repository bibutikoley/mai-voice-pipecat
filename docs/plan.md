# mai-voice-pipecat — Build Plan

> Historical planning document. The "Locked decisions" and later sections record
> the original plan; for current behavior use the other docs and the
> Implementation status at the bottom (which supersedes anything above it).

Voice AI monorepo: a Dockerized Pipecat server with native Android and iOS clients.

## Locked decisions

| Area | Decision |
|---|---|
| Server runtime | **Docker only** — no host-run server, no Homebrew Pipecat |
| Docker base | `ghcr.io/astral-sh/uv:python3.12-trixie-slim` (no `dailyco/pipecat-base`; that image is Pipecat Cloud runtime) |
| Python tooling | `uv` for dependency management, lockfile, tests, lint (inside the image for the server) |
| Transport | SmallWebRTC (`POST /api/offer`), port 7860 |
| STT default | Moonshine `small-streaming` (English, local, ONNX) |
| TTS default | Kokoro v1.0 ONNX, voice `af_heart` (en-US, local) |
| LLM | `LLM_MODE=stub` until credentials arrive; then `openai_compatible` with `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` |
| Model storage | Default host caches, bind-mounted into the container; HF CLI (`hf`) on host for manual pulls |
| Model lifecycle | `MODEL_LIFECYCLE=session` (default): models released at session end; process exit frees all |
| Clients | Native Android (Compose) + iOS (SwiftUI), full-featured UI |

## Architecture

```
iOS app ─┐
         ├─ SmallWebRTC (audio) ──► Docker: Pipecat bot (port 7860)
Android ─┘                          └─ VAD (Silero) → STT → LLM → TTS
```

- Client starts session via the Pipecat development runner (`POST /api/offer` for SmallWebRTC).
- STT and TTS providers are chosen independently by env vars; LLM is either a canned stub or any
  OpenAI-compatible endpoint.
- Models load per session and are explicitly released on disconnect (`cleanup()` → `gc.collect()` →
  `malloc_trim`), so idle memory does not grow. `MODEL_LIFECYCLE=warm` keeps them cached until the
  container stops.

## Repo layout

```
mai-voice-pipecat/
├── .gitignore  README.md  Makefile
├── docker-compose.yml              # backend + one-shot model-fetch service
├── docs/                           # plan.md, architecture.md, local-development.md, providers.md, sdk-notes.md
├── scripts/
├── backend/
│   ├── pyproject.toml  uv.lock  Dockerfile  .dockerignore  .env.example
│   ├── bot.py                      # entrypoint → pipecat runner (--host 0.0.0.0)
│   └── mai_voice/
│       ├── config.py               # env parsing/validation
│       ├── pipeline.py             # per-session pipeline assembly
│       ├── lifecycle.py            # ReleaseOnCleanup mixin, gc + malloc_trim
│       ├── tools/fetch_models.py   # warm default caches (run via one-shot container)
│       └── providers/
│           ├── registry.py         # create_stt()/create_tts() from env, lazy imports
│           ├── stt_moonshine.py  stt_whisper.py  stt_qwen.py  stt_deepgram.py
│           ├── tts_kokoro.py     tts_piper.py    tts_qwen.py  tts_cartesia.py
│           └── llm_stub.py       llm_openai_compatible.py
└── frontend/
    ├── mai-voice-android/          # Compose app, Pipecat Android SDK
    └── mai-voice-ios/              # SwiftUI app, Pipecat iOS SDK
```

## Provider switching (env vars)

```env
# defaults
STT_PROVIDER=moonshine            # moonshine | whisper | qwen | deepgram
TTS_PROVIDER=kokoro               # kokoro | piper | qwen | cartesia
LLM_MODE=stub                     # stub | openai_compatible
MODEL_LIFECYCLE=session           # session | warm

# LLM (when not stub)
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=

# provider options
MOONSHINE_MODEL=small_streaming
KOKORO_VOICE=af_heart
QWEN_ASR_MODEL=Qwen/Qwen3-ASR-0.6B
QWEN_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice
```

STT and TTS are independent — every combination is valid:

| STT | TTS | Notes |
|---|---|---|
| moonshine | kokoro | default, lightest |
| qwen | kokoro | Qwen ASR only |
| moonshine | qwen | Qwen TTS only |
| qwen | qwen | both Qwen |
| whisper / deepgram | piper / cartesia | require extras (`EXTRAS=...` at image build) |

Changing providers = edit `.env` + `docker compose restart`. No rebuild for defaults and Qwen (deps
are baked into the default image).

Adding a provider = one module in `mai_voice/providers/` + one registry entry. Each module imports its
service lazily and raises a clear install hint when dependencies are missing.

## Models

Nothing is baked into the image. Models live in default host caches and are bind-mounted:

| Model | Default host cache | Container path |
|---|---|---|
| Kokoro TTS | `~/.cache/pipecat/kokoro-onnx` | `/root/.cache/pipecat/kokoro-onnx` (rw) |
| Moonshine STT | `~/Library/Caches/moonshine_voice` (`MOONSHINE_VOICE_CACHE`) | `/root/.cache/moonshine_voice` (rw) |
| HF cache | `~/.cache/huggingface` | `/root/.cache/huggingface` (ro) |

`make models` runs a one-shot container that warms the Moonshine cache (using the library's own
verified downloader; the official HF mirror `moonshine-ai/moonshine-voice-assets` is documented as
the offline fallback) and verifies the Kokoro files. Kokoro's 310 MB model is already present on the
host.

### Memory lifecycle

- `MODEL_LIFECYCLE=session` (default): services are created inside `bot()` per session; on disconnect
  `cleanup()` drops model references, then `gc.collect()` and glibc `malloc_trim(0)` return RAM to
  the OS. GPU/MPS caches cleared where applicable.
- `MODEL_LIFECYCLE=warm`: models cached process-wide for faster session starts; released when the
  server stops.
- Server stop (SIGINT/SIGTERM, `docker compose stop`) cancels sessions, runs cleanup, and process
  exit reclaims anything left.

### Qwen packaging note

`qwen-asr` (transformers==4.57.6) and `qwen-tts` (transformers==4.57.3) disagree on a shared library,
which matters only while resolving the image install (both are installed by default; only the
selected provider is imported at runtime). Staged mitigation:

1. `[tool.uv] override-dependencies` forces one transformers version; a build-time smoke test loads
   each Qwen adapter.
2. If one package breaks under the shared version, Qwen adapters move behind isolated helper
   processes with independent dependency sets — which also releases their memory on session end.

Qwen TTS generation is non-streaming on CPU; playback is chunked after generation. Expect seconds per
sentence on a Mac CPU — fine for development, not for production latency.

## Phases

1. **Scaffold** — `git init` (no commits unless asked), root `.gitignore`, README, docs, Makefile,
   compose skeleton.
2. **Backend** — uv project, provider registry, lifecycle, stub LLM, pipeline, runner entry, tests.
3. **Docker** — uv-slim image + `espeak-ng`/audio libs, cache bind-mounts, model-fetch service,
   healthcheck. Verify: browser `/client` voice loop with stub LLM and real local STT/TTS.
4. **Android** — `ai.pipecat:client` + `small-webrtc-transport`, ViewModel/StateFlow mapping, DataStore
   server URL (`http://10.0.2.2:7860`), full UI: orb, transcripts, mute, settings, errors.
5. **iOS** — SPM `pipecat-client-ios` 1.3.0 + `pipecat-client-ios-small-webrtc` 1.3.0, mic + ATS
   settings, `@Observable` model, same UI surface (`http://localhost:7860`).
6. **E2E + docs** — both simulators against the container; memory-release check; finalize docs.

## Verification per phase

- Backend: `uv run pytest`, `uv run ruff check`, `/status` health endpoint.
- Docker: `docker compose up`, browser talk test, `docker stats` memory before/after a session,
  `docker compose stop` leaves no processes.
- Android: `./gradlew :app:assembleDebug`, emulator connects and talks.
- iOS: `xcodebuild build` for simulator, app connects and talks.

## Risks

- Qwen packages' transformers pin conflict (mitigation above).
- Qwen CPU latency in Docker on Mac (acceptable for dev; Moonshine/Kokoro remain defaults).
- Physical devices need the Mac's LAN IP in app settings; simulators use localhost/`10.0.2.2`.
- Production TURN/coturn is a later milestone; SmallWebRTC is fine for local development.

## Open items

- LLM base URL and key (later; stub mode until then).
- Optional cloud providers (Deepgram/Cartesia) and lighter alternatives (Whisper/Piper) are wired in
  the registry but only installed when requested via image build arg `EXTRAS`.

## Implementation status (Sep 14, 2026)

Built and verified:

- Backend + Docker: providers registry, session-scoped model lifecycle, stub LLM,
  `/client` browser loop, healthcheck. aiortc E2E test posted an SDP offer, sent
  Qwen-generated speech, and the recorded reply round-tripped through Qwen ASR as
  "Hi. Stub reply. You said this is a local Qwen voice test."
- Memory: a session peaks ~1.2 GB and returns to ~300 MB after disconnect
  (models released in logs); consecutive sessions reuse the same footprint. A
  torch import in `release_memory()` was the culprit for a ~450 MB residual and
  was removed (torch is only touched when already loaded).
- Qwen: both adapters load under the forced `transformers==4.57.6`; TTS→ASR round
  trip verified. CPU TTS is slow (~19 s for a 4 s utterance) — documented.
- Android: full UI (orb, transcripts, mute, settings, error banner) built with
  `ai.pipecat:client:1.2.0` + `small-webrtc-transport:1.2.1`; connects to the
  Docker server from the emulator and renders the greeting transcript.
- iOS: full UI with SPM packages 1.3.0; connects from the simulator
  (`--auto-connect` flag for testing) and renders user/bot transcripts.
- Backend tests (38) and ruff pass; Android `assembleDebug` and iOS
  `xcodebuild` succeed.

Later additions (current state):

- **MLX host servers**: STT and TTS run natively on Apple Silicon as two
  independent processes — `make stt-server` (127.0.0.1:8001) and
  `make tts-server` (127.0.0.1:8002) — called by the container over HTTP via
  `host.docker.internal`. Loopback-only: LAN devices get connection refused.
  `make stt-stop` / `make tts-stop` are independent of each other and of the
  Docker server. This replaces in-container inference for the default setup.
- **Sarvam AI**: `STT_PROVIDER=sarvam`, `TTS_PROVIDER=sarvam`, `LLM_MODE=sarvam`
  (Indic languages); SDK is in the default image, so switching is env-only.
- **Voice output cleanup**: markdown/emoji text filters (`TTS_TEXT_FILTERS`) and
  a +6 dB gain stage (`TTS_GAIN_DB`), plus a system prompt that keeps replies to
  one or two spoken sentences.
- **Speaker routing**: both apps default to the loudspeaker with a persisted
  speaker/earpiece toggle.
- Defaults are now `STT_PROVIDER=mlx` / `TTS_PROVIDER=mlx`; in-container
  providers remain available as fallbacks.

Deviations from the plan as written above:

- No `scripts/` directory — Makefile targets cover build/run/models/test/lint.
- `dailyco/pipecat-base` was not used (Pipecat Cloud runtime); the image builds
  from `ghcr.io/astral-sh/uv:python3.12-trixie-slim`.
- Moonshine cache warm-up uses the library's verified downloader (the HF mirror
  remains an offline fallback), since its cache layout is CDN-shaped.
- The iOS app has a `--auto-connect` launch flag (testing affordance).

