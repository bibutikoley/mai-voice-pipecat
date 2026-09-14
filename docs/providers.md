# Providers

STT and TTS are independent; any combination is valid. The LLM is the stub, any
OpenAI-compatible endpoint, or Sarvam. Switch by editing `backend/.env` and
running `make restart` — no rebuild needed for `mlx`, `qwen`, or `sarvam`.

```env
STT_PROVIDER=mlx         # mlx | moonshine | whisper | qwen | deepgram | sarvam
TTS_PROVIDER=mlx         # mlx | kokoro | piper | qwen | cartesia | sarvam
LLM_MODE=stub            # stub | openai_compatible | sarvam
MODEL_LIFECYCLE=session  # session | warm
```

| STT | TTS | Loads into memory |
|---|---|---|
| **mlx** | **mlx** | nothing in the container — models run on the Mac |
| mlx | kokoro | Kokoro in the container |
| moonshine | mlx | Moonshine in the container |
| moonshine | kokoro | `moonshine_voice`, `kokoro_onnx` |
| qwen | kokoro | `qwen_asr` |
| moonshine | qwen | `qwen_tts` |
| qwen | qwen | both |
| sarvam | any | nothing (cloud API) |
| any | sarvam | nothing (cloud API) |
| whisper / deepgram | piper / cartesia | optional extras |

## Providers

| Name | Kind | Package / cache | Notes |
|---|---|---|---|
| **MLX (host)** | STT/TTS | Mac host, `mlx-audio` | Apple Silicon Metal inference; loopback-only HTTP; models stay warm |
| **Sarvam AI** | STT/TTS/LLM | built into the default image | Cloud; Indic languages; streaming WS STT/TTS; `SARVAM_API_KEY` required |
| Moonshine | STT | `pipecat-ai[moonshine]`, CDN cache | English, ONNX CPU, fast; default model `small-streaming` |
| Whisper | STT | `pipecat-ai[whisper]` extra, HF cache | faster-whisper `base.en`; multilingual capable |
| Qwen3-ASR | STT | `qwen-asr`, HF cache | local transformers backend, CPU; segmented (not streaming) |
| Deepgram | STT | `cloud` extra | cloud API key |
| Kokoro | TTS | `pipecat-ai[kokoro]`, `~/.cache/pipecat/kokoro-onnx` | ONNX CPU, `af_heart` default voice |
| Piper | TTS | `piper` extra | GPL-3; voices from HF |
| Qwen3-TTS | TTS | `qwen-tts`, HF cache | local, non-streaming generation chunked for playback |
| Cartesia | TTS | `cloud` extra | cloud API key |

## Sarvam AI (Indic languages)

Sarvam provides cloud STT, TTS, and LLM for Indian languages. The SDK ships in
the default image — switching is env-only:

```env
STT_PROVIDER=sarvam          # saaras:v4, WebSocket streaming
TTS_PROVIDER=sarvam          # bulbul:v3, voice shubh
LLM_MODE=sarvam              # optional: sarvam-105b
SARVAM_API_KEY=...
SARVAM_LANGUAGE=hi-IN        # en-IN, hi-IN, bn-IN, ta-IN, te-IN, ...
SARVAM_TTS_VOICE=shubh       # also: aditya, ritu, priya, neha, rahul, pooja, ...
```

Notes:
- STT auto-detects language for `saaras:v4`; we pass `SARVAM_LANGUAGE` explicitly.
- TTS voices are `bulbul:v3` speakers; text filters and the gain stage still
  apply before/after synthesis.
- `LLM_MODE=sarvam` sends Sarvam's `api-subscription-key` header (the plain
  `openai_compatible` mode does not, so Sarvam's LLM needs this provider).
- Mix freely, e.g. `STT_PROVIDER=sarvam` + `TTS_PROVIDER=mlx` for Indic speech
  in and Qwen voice out.

## Apple Silicon (MLX) servers

The recommended setup runs STT and TTS natively on the Mac with Metal, as two
independent processes so you can change/restart either without touching the
others:

```bash
make stt-server        # terminal 1: STT on 127.0.0.1:8001
make tts-server        # terminal 2: TTS on 127.0.0.1:8002
make up                # terminal 3: Docker Pipecat server on :7860
```

```env
STT_PROVIDER=mlx
TTS_PROVIDER=mlx
MLX_STT_BASE_URL=http://host.docker.internal:8001
MLX_TTS_BASE_URL=http://host.docker.internal:8002
MLX_STT_MODEL=mlx-community/Qwen3-ASR-0.6B-8bit
MLX_TTS_MODEL=mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-8bit
MLX_TTS_VOICE=Ryan
```

- Measured on an M-series Mac: warm STT ≈ 0.2s, warm TTS ≈ 0.7× realtime.
- First request per model downloads from the HF hub and loads it (STT ≈ 20s,
  TTS ≈ 100s including download); after that models stay warm in that server
  process.
- Stop either server without affecting the others: `make stt-stop`,
  `make tts-stop`; the Docker server stops with `make down`.
- Model alternatives: `mlx-community/Qwen3-ASR-1.7B-8bit` (more accurate),
  `mlx-community/whisper-large-v3-turbo-asr-fp16`, and for TTS
  `mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-bf16` or
  `mlx-community/Kokoro-82M-bf16`.
- **Security**: both servers bind `127.0.0.1` only. The container reaches them
  via `host.docker.internal`; phones and other LAN devices get connection
  refused. Never start them with `--host 0.0.0.0`.

## Speech clean-up

Two stages run between the LLM and the voice, configured in `backend/.env`:

- `TTS_TEXT_FILTERS=markdown,emoji` (default) strips markdown formatting and
  emoji before synthesis, so the voice never reads "asterisk" or "hashtag".
  Accepts any comma-separated combination of `markdown`, `emoji`, or `none`.
- `TTS_GAIN_DB=6.0` (default) raises output loudness with clipping protection;
  0 disables it.

## Qwen notes

- Default models come from the existing HF cache:
  `Qwen/Qwen3-ASR-0.6B` and `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` (1.7B variants
  are drop-in via `QWEN_ASR_MODEL` / `QWEN_TTS_MODEL`).
- `qwen-asr` pins `transformers==4.57.6` and `qwen-tts` pins `==4.57.3`. Both are
  installed in the default image; `[tool.uv] override-dependencies` forces one
  version and both adapters were smoke-tested against it (imports, model load,
  and a TTS→ASR round trip). If a future version breaks, the fallback is
  isolating the Qwen adapters in helper processes.
- CPU latency (Mac, Docker): ASR ≈ 1–3 s per utterance, TTS ≈ several seconds per
  sentence (≈19 s for a 4 s utterance in testing). Fine for development, not for
  production latency; use the MLX servers (default) or Moonshine + Kokoro for
  lower-latency in-container options.
- Qwen TTS uses `QWEN_TTS_SPEAKER` (e.g. `Ryan`, `Aiden`) and
  `QWEN_TTS_LANGUAGE`.

## LLM

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://ollama.com/v1     # Ollama Cloud
LLM_API_KEY=...                        # your Ollama API key
LLM_MODEL=gpt-oss:120b
```

Other common endpoints:

```env
LLM_BASE_URL=http://host.docker.internal:11434/v1   # Ollama on the Mac
LLM_BASE_URL=https://api.openai.com/v1              # OpenAI
```

Works with OpenAI, Ollama (cloud or host), vLLM, LM Studio, Groq, and any
OpenAI-compatible server. From the container, a server on the Mac is reachable
via `http://host.docker.internal:<port>`.

`LLM_MODE=stub` replies with canned text and needs no keys — the full voice loop
still runs (mic → STT → reply → TTS).

## Adding a provider

1. Add `mai_voice/providers/stt_<name>.py` (or `tts_<name>.py`) with a
   `create(settings) -> FrameProcessor` function. Import the pipecat service
   lazily and mix in `ReleasesModels` with the model attribute name so memory is
   released per session:
   ```python
   class MySTT(ReleasesModels, VendorSTTService):
       _model_attrs = ("_model",)
   ```
2. Register it in `mai_voice/providers/registry.py`.
3. Add the dependency either to the default dependencies (if it should always be
   available, like Sarvam) or as an optional extra in `backend/pyproject.toml`
   (`[project.optional-dependencies]`, installed with `EXTRAS=<name> make build`),
   and set a matching hint on the `ProviderSpec`.
4. Add config fields/defaults in `mai_voice/config.py` and document them in
   `backend/.env.example`.
