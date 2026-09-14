"""Unit tests for the provider registry."""

from __future__ import annotations

import pytest

from mai_voice.config import ConfigError, Settings
from mai_voice.providers import registry


def test_registry_contains_expected_providers():
    assert set(registry.STT_PROVIDERS) == {"moonshine", "whisper", "qwen", "deepgram", "mlx"}
    assert set(registry.TTS_PROVIDERS) == {"kokoro", "piper", "qwen", "cartesia", "mlx"}
    assert set(registry.LLM_PROVIDERS) == {"stub", "openai_compatible"}


def test_unknown_provider_lists_alternatives():
    with pytest.raises(ConfigError, match="Available"):
        registry.create_stt(Settings(stt_provider="nope"))


def test_missing_extra_raises_install_hint():
    # Piper is an optional extra and is not installed in the default image.
    with pytest.raises(ConfigError) as exc:
        registry.create_tts(Settings(tts_provider="piper"))
    assert "not installed" in str(exc.value)


def test_stub_llm_is_created_without_keys():
    llm = registry.create_llm(Settings(llm_mode="stub"))
    assert type(llm).__name__ == "StubLLM"
