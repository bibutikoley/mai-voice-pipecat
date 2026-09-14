"""Unit tests for the MLX TTS provider's WAV decoding."""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf

from mai_voice.providers.tts_mlx import wav_to_pcm16


def _wav_bytes(data: np.ndarray, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    sf.write(buffer, data, sample_rate, format="WAV", subtype="PCM_16")
    return buffer.getvalue()


def test_decodes_mono_wav():
    samples = np.sin(np.linspace(0, 2 * np.pi, 480)).astype(np.float32)
    pcm, sample_rate = wav_to_pcm16(_wav_bytes(samples, 24000))
    decoded = np.frombuffer(pcm, dtype=np.int16)
    assert sample_rate == 24000
    assert len(decoded) == 480
    assert np.max(np.abs(decoded)) > 1000


def test_downmixes_stereo_wav():
    left = np.full(240, 0.5, dtype=np.float32)
    right = np.full(240, 0.5, dtype=np.float32)
    stereo = np.stack([left, right], axis=1)
    pcm, sample_rate = wav_to_pcm16(_wav_bytes(stereo, 16000))
    decoded = np.frombuffer(pcm, dtype=np.int16)
    assert sample_rate == 16000
    assert len(decoded) == 240
