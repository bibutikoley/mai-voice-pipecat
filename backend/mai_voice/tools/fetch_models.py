"""Warm the default model caches.

Run inside the container so host caches are populated in exactly the layout the
server expects:

    docker compose --profile tools run --rm models

- Moonshine: downloads the configured model into the Moonshine cache
  (`MOONSHINE_VOICE_CACHE`, default per-platform cache dir) using the library's
  own verified downloader. The official HF mirror
  `moonshine-ai/moonshine-voice-assets` is available as an offline fallback.
- Kokoro: ensures the ONNX model and voices files exist in
  `~/.cache/pipecat/kokoro-onnx`.
- Qwen models are managed by the `hf` CLI / Hugging Face cache and load on
  demand at session time.
"""

from __future__ import annotations

import sys

from loguru import logger

from mai_voice.config import load_settings


def warm_moonshine(model: str) -> None:
    from moonshine_voice import get_model_for_language, string_to_model_arch
    from moonshine_voice.download_file import get_cache_dir

    logger.info(f"Warming Moonshine cache (model={model}) at {get_cache_dir()}")
    model_path, arch = get_model_for_language("en", string_to_model_arch(model))
    logger.info(f"Moonshine ready: {model_path}")


def warm_kokoro() -> None:
    from pipecat.services.kokoro.tts import KOKORO_CACHE_DIR, _ensure_model_files

    model_path = KOKORO_CACHE_DIR / "kokoro-v1.0.onnx"
    voices_path = KOKORO_CACHE_DIR / "voices-v1.0.bin"
    logger.info(f"Warming Kokoro cache at {KOKORO_CACHE_DIR}")
    _ensure_model_files(model_path, voices_path)
    logger.info(f"Kokoro ready: {model_path}")


def main() -> int:
    settings = load_settings()

    if settings.stt_provider == "moonshine":
        warm_moonshine(settings.moonshine_model)
    else:
        logger.info(
            f"Skipping Moonshine warm-up (STT_PROVIDER={settings.stt_provider})"
        )

    if settings.tts_provider == "kokoro":
        warm_kokoro()
    else:
        logger.info(f"Skipping Kokoro warm-up (TTS_PROVIDER={settings.tts_provider})")

    if settings.stt_provider == "qwen":
        logger.info(
            "Qwen ASR models load from the Hugging Face cache on first use "
            f"({settings.qwen_asr_model})."
        )
    if settings.tts_provider == "qwen":
        logger.info(
            "Qwen TTS models load from the Hugging Face cache on first use "
            f"({settings.qwen_tts_model})."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
