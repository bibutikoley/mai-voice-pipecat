"""Environment-driven configuration for the mai-voice server.

The STT and TTS providers are independent: any STT can be paired with any TTS.
`load_settings()` reads the process environment (dotenv is loaded in bot.py) and
validates that the selected providers are known and that cloud providers have
their credentials before the pipeline is built.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

STT_PROVIDERS = ("moonshine", "whisper", "qwen", "deepgram")
TTS_PROVIDERS = ("kokoro", "piper", "qwen", "cartesia")
LLM_MODES = ("stub", "openai_compatible")
MODEL_LIFECYCLES = ("session", "warm")


class ConfigError(RuntimeError):
    """Raised when the environment configuration is invalid."""


@dataclass(frozen=True)
class Settings:
    """Validated server settings."""

    # Provider selection
    stt_provider: str = "moonshine"
    tts_provider: str = "kokoro"
    llm_mode: str = "stub"
    model_lifecycle: str = "session"

    # LLM (openai_compatible mode)
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None

    # STT options
    moonshine_model: str = "small-streaming"
    whisper_model: str = "base.en"
    qwen_asr_model: str = "Qwen/Qwen3-ASR-0.6B"
    qwen_asr_language: str = "English"
    qwen_asr_device: str = "cpu"
    deepgram_api_key: str | None = None

    # TTS options
    kokoro_voice: str = "af_heart"
    piper_voice: str = "en_US-ryan-high"
    qwen_tts_model: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"
    qwen_tts_speaker: str = "Ryan"
    qwen_tts_language: str = "English"
    qwen_tts_device: str = "cpu"
    cartesia_api_key: str | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 7860


def _bool_env(env: Mapping[str, str], key: str, default: bool) -> bool:
    raw = env.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build and validate settings from an environment mapping."""
    env = os.environ if env is None else env

    provider = (env.get("STT_PROVIDER") or "moonshine").strip().lower()
    if provider not in STT_PROVIDERS:
        raise ConfigError(
            f"Unknown STT_PROVIDER '{provider}'. Available: {', '.join(STT_PROVIDERS)}"
        )

    tts_provider = (env.get("TTS_PROVIDER") or "kokoro").strip().lower()
    if tts_provider not in TTS_PROVIDERS:
        raise ConfigError(
            f"Unknown TTS_PROVIDER '{tts_provider}'. Available: {', '.join(TTS_PROVIDERS)}"
        )

    llm_mode = (env.get("LLM_MODE") or "stub").strip().lower()
    if llm_mode not in LLM_MODES:
        raise ConfigError(f"Unknown LLM_MODE '{llm_mode}'. Available: {', '.join(LLM_MODES)}")

    lifecycle = (env.get("MODEL_LIFECYCLE") or "session").strip().lower()
    if lifecycle not in MODEL_LIFECYCLES:
        raise ConfigError(
            f"Unknown MODEL_LIFECYCLE '{lifecycle}'. Available: {', '.join(MODEL_LIFECYCLES)}"
        )

    settings = Settings(
        stt_provider=provider,
        tts_provider=tts_provider,
        llm_mode=llm_mode,
        model_lifecycle=lifecycle,
        llm_base_url=env.get("LLM_BASE_URL") or None,
        llm_api_key=env.get("LLM_API_KEY") or None,
        llm_model=env.get("LLM_MODEL") or None,
        moonshine_model=env.get("MOONSHINE_MODEL") or "small-streaming",
        whisper_model=env.get("WHISPER_MODEL") or "base.en",
        qwen_asr_model=env.get("QWEN_ASR_MODEL") or "Qwen/Qwen3-ASR-0.6B",
        qwen_asr_language=env.get("QWEN_ASR_LANGUAGE") or "English",
        qwen_asr_device=env.get("QWEN_ASR_DEVICE") or "cpu",
        deepgram_api_key=env.get("DEEPGRAM_API_KEY") or None,
        kokoro_voice=env.get("KOKORO_VOICE") or "af_heart",
        piper_voice=env.get("PIPER_VOICE") or "en_US-ryan-high",
        qwen_tts_model=env.get("QWEN_TTS_MODEL") or "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        qwen_tts_speaker=env.get("QWEN_TTS_SPEAKER") or "Ryan",
        qwen_tts_language=env.get("QWEN_TTS_LANGUAGE") or "English",
        qwen_tts_device=env.get("QWEN_TTS_DEVICE") or "cpu",
        cartesia_api_key=env.get("CARTESIA_API_KEY") or None,
        host=env.get("HOST") or "0.0.0.0",
        port=int(env.get("PORT") or "7860"),
    )

    if settings.llm_mode == "openai_compatible":
        missing = [
            key
            for key, value in (
                ("LLM_BASE_URL", settings.llm_base_url),
                ("LLM_API_KEY", settings.llm_api_key),
                ("LLM_MODEL", settings.llm_model),
            )
            if not value
        ]
        if missing:
            raise ConfigError(
                "LLM_MODE=openai_compatible requires: " + ", ".join(missing)
            )

    if settings.stt_provider == "deepgram" and not settings.deepgram_api_key:
        raise ConfigError("STT_PROVIDER=deepgram requires DEEPGRAM_API_KEY")

    if settings.tts_provider == "cartesia" and not settings.cartesia_api_key:
        raise ConfigError("TTS_PROVIDER=cartesia requires CARTESIA_API_KEY")

    return settings
