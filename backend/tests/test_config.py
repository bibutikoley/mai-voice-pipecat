"""Unit tests for environment configuration."""

from __future__ import annotations

import pytest

from mai_voice.config import ConfigError, load_settings


def test_defaults_need_no_keys():
    settings = load_settings({})
    assert settings.stt_provider == "moonshine"
    assert settings.tts_provider == "kokoro"
    assert settings.llm_mode == "stub"
    assert settings.model_lifecycle == "session"
    assert settings.kokoro_voice == "af_heart"
    assert settings.qwen_asr_model == "Qwen/Qwen3-ASR-0.6B"
    assert settings.qwen_tts_model == "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice"


@pytest.mark.parametrize(
    ("stt", "tts"),
    [
        ("moonshine", "kokoro"),
        ("qwen", "kokoro"),
        ("moonshine", "qwen"),
        ("qwen", "qwen"),
    ],
)
def test_stt_tts_combinations_are_independent(stt, tts):
    settings = load_settings({"STT_PROVIDER": stt, "TTS_PROVIDER": tts})
    assert settings.stt_provider == stt
    assert settings.tts_provider == tts


def test_unknown_stt_provider_is_rejected():
    with pytest.raises(ConfigError, match="Unknown STT_PROVIDER"):
        load_settings({"STT_PROVIDER": "bogus"})


def test_unknown_tts_provider_is_rejected():
    with pytest.raises(ConfigError, match="Unknown TTS_PROVIDER"):
        load_settings({"TTS_PROVIDER": "bogus"})


def test_openai_compatible_requires_credentials():
    with pytest.raises(ConfigError) as exc:
        load_settings({"LLM_MODE": "openai_compatible"})
    message = str(exc.value)
    assert "LLM_BASE_URL" in message
    assert "LLM_API_KEY" in message
    assert "LLM_MODEL" in message


def test_openai_compatible_with_credentials_is_valid():
    settings = load_settings(
        {
            "LLM_MODE": "openai_compatible",
            "LLM_BASE_URL": "http://host.docker.internal:11434/v1",
            "LLM_API_KEY": "test-key",
            "LLM_MODEL": "llama3.2:3b",
        }
    )
    assert settings.llm_base_url == "http://host.docker.internal:11434/v1"
    assert settings.llm_model == "llama3.2:3b"


def test_deepgram_requires_api_key():
    with pytest.raises(ConfigError, match="DEEPGRAM_API_KEY"):
        load_settings({"STT_PROVIDER": "deepgram"})


def test_cartesia_requires_api_key():
    with pytest.raises(ConfigError, match="CARTESIA_API_KEY"):
        load_settings({"TTS_PROVIDER": "cartesia"})


def test_invalid_model_lifecycle_is_rejected():
    with pytest.raises(ConfigError, match="MODEL_LIFECYCLE"):
        load_settings({"MODEL_LIFECYCLE": "forever"})


def test_sarvam_defaults():
    settings = load_settings({"SARVAM_API_KEY": "test-key"})
    assert settings.sarvam_stt_model == "saaras:v4"
    assert settings.sarvam_tts_model == "bulbul:v3"
    assert settings.sarvam_tts_voice == "shubh"
    assert settings.sarvam_language == "en-IN"


@pytest.mark.parametrize("env", [{"STT_PROVIDER": "sarvam"}, {"TTS_PROVIDER": "sarvam"}])
def test_sarvam_audio_requires_api_key(env):
    with pytest.raises(ConfigError, match="SARVAM_API_KEY"):
        load_settings(env)


def test_sarvam_llm_requires_api_key():
    with pytest.raises(ConfigError, match="SARVAM_API_KEY"):
        load_settings({"LLM_MODE": "sarvam"})


def test_sarvam_language_helper_accepts_iso_codes():
    from mai_voice.providers._languages import pipecat_language

    assert pipecat_language("hi-IN").value == "hi-IN"
    with pytest.raises(ConfigError, match="Unsupported language"):
        pipecat_language("klingon")
