# Providers

STT and TTS are independent; any combination is valid. LLM is either the stub
or any OpenAI-compatible endpoint. Switch by editing `backend/.env` and running
`make restart` — no rebuild for the default and Qwen providers.

```env
STT_PROVIDER=moonshine   # moonshine | whisper | qwen | deepgram
TTS_PROVIDER=kokoro      # kokoro | piper | qwen | cartesia
LLM_MODE=stub            # stub | openai_compatible
MODEL_LIFECYCLE=session  # session | warm
```

| STT | TTS | Loads into memory |
|---|---|---|
| moonshine | kokoro | `moonshine_voice`, `kokoro_onnx` |
| qwen | kokoro | `qwen_asr` |
| moonshine | qwen | `qwen_tts` |
| qwen | qwen | both |
| whisper / deepgram | piper / cartesia | optional extras |

## Providers

| Name | Kind | Package / cache | Notes |
|---|---|---|---|
| Moonshine | STT | `pipecat-ai[moonshine]`, CDN cache | English, ONNX CPU, fast; default model `small-streaming` |
| Whisper | STT | `pipecat-ai[whisper]` extra, HF cache | faster-whisper `base.en`; multilingual capable |
| Qwen3-ASR | STT | `qwen-asr`, HF cache | local transformers backend, CPU; segmented (not streaming) |
| Deepgram | STT | `cloud` extra | cloud API key |
| Kokoro | TTS | `pipecat-ai[kokoro]`, `~/.cache/pipecat/kokoro-onnx` | ONNX CPU, `af_heart` default voice |
| Piper | TTS | `piper` extra | GPL-3; voices from HF |
| Qwen3-TTS | TTS | `qwen-tts`, HF cache | local, non-streaming generation chunked for playback |
| Cartesia | TTS | `cloud` extra | cloud API key |

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
  production latency; Moonshine + Kokoro are the fast defaults.
- Qwen TTS uses `QWEN_TTS_SPEAKER` (e.g. `Ryan`, `Aiden`) and
  `QWEN_TTS_LANGUAGE`.

## LLM

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=http://host.docker.internal:11434/v1   # Ollama on the host
LLM_API_KEY=ollama
LLM_MODEL=llama3.2:3b
```

Works with OpenAI, vLLM, LM Studio, Groq, and any OpenAI-compatible server.
From the container, a server on the Mac is reachable via
`http://host.docker.internal:<port>`.

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
3. Add the dependency as an optional extra in `backend/pyproject.toml`
   (`[project.optional-dependencies]`) and, if it needs an install hint, set it
   on the `ProviderSpec`.
4. Add config fields/defaults in `mai_voice/config.py` and document them in
   `backend/.env.example`.
