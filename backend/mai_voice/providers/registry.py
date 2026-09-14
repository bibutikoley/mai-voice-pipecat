"""Provider registry: resolve env-selected providers to pipecat services.

Provider modules are imported lazily so that:
- only the selected provider's dependencies are loaded at runtime, and
- a missing optional dependency produces a clear install hint instead of an
  import error at startup.

Adding a provider: create `stt_<name>.py` / `tts_<name>.py` with a
`create(settings) -> FrameProcessor` function, then add its spec below.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from mai_voice.config import ConfigError, Settings


@dataclass(frozen=True)
class ProviderSpec:
    module: str
    hint: str = ""


STT_PROVIDERS: dict[str, ProviderSpec] = {
    "moonshine": ProviderSpec("mai_voice.providers.stt_moonshine"),
    "whisper": ProviderSpec(
        "mai_voice.providers.stt_whisper",
        hint='Build/install with the "whisper" extra (EXTRAS=whisper for Docker).',
    ),
    "qwen": ProviderSpec("mai_voice.providers.stt_qwen"),
    "mlx": ProviderSpec("mai_voice.providers.stt_mlx"),
    "sarvam": ProviderSpec(
        "mai_voice.providers.stt_sarvam",
        hint="The Sarvam SDK should be part of the default image (sarvamai).",
    ),
    "deepgram": ProviderSpec(
        "mai_voice.providers.stt_deepgram",
        hint='Build/install with the "cloud" extra (EXTRAS=cloud for Docker).',
    ),
}

TTS_PROVIDERS: dict[str, ProviderSpec] = {
    "kokoro": ProviderSpec("mai_voice.providers.tts_kokoro"),
    "piper": ProviderSpec(
        "mai_voice.providers.tts_piper",
        hint='Build/install with the "piper" extra (EXTRAS=piper for Docker).',
    ),
    "qwen": ProviderSpec("mai_voice.providers.tts_qwen"),
    "mlx": ProviderSpec("mai_voice.providers.tts_mlx"),
    "sarvam": ProviderSpec(
        "mai_voice.providers.tts_sarvam",
        hint="The Sarvam SDK should be part of the default image (sarvamai).",
    ),
    "cartesia": ProviderSpec(
        "mai_voice.providers.tts_cartesia",
        hint='Build/install with the "cloud" extra (EXTRAS=cloud for Docker).',
    ),
}

LLM_PROVIDERS: dict[str, ProviderSpec] = {
    "stub": ProviderSpec("mai_voice.providers.llm_stub"),
    "openai_compatible": ProviderSpec("mai_voice.providers.llm_openai_compatible"),
    "sarvam": ProviderSpec(
        "mai_voice.providers.llm_sarvam",
        hint="The Sarvam SDK should be part of the default image (sarvamai).",
    ),
}


def _resolve(registry: dict[str, ProviderSpec], kind: str, name: str):
    spec = registry.get(name)
    if spec is None:
        raise ConfigError(f"Unknown {kind} '{name}'. Available: {', '.join(sorted(registry))}")
    try:
        module = import_module(spec.module)
    except ImportError as exc:
        message = f"{kind} provider '{name}' is not installed"
        if spec.hint:
            message += f". {spec.hint}"
        raise ConfigError(message) from exc
    return module


def create_stt(settings: Settings):
    """Create the configured speech-to-text service."""
    module = _resolve(STT_PROVIDERS, "STT provider", settings.stt_provider)
    return module.create(settings)


def create_tts(settings: Settings):
    """Create the configured text-to-speech service."""
    module = _resolve(TTS_PROVIDERS, "TTS provider", settings.tts_provider)
    return module.create(settings)


def create_llm(settings: Settings):
    """Create the configured language model service."""
    module = _resolve(LLM_PROVIDERS, "LLM provider", settings.llm_mode)
    return module.create(settings)
