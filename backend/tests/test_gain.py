"""Unit tests for the output audio gain stage."""

from __future__ import annotations

import numpy as np

from mai_voice.processors.gain import (
    MAX_GAIN_DB,
    MIN_GAIN_DB,
    AudioGainProcessor,
    apply_gain,
    db_to_linear,
)


def _pcm(values: list[int]) -> bytes:
    return np.array(values, dtype=np.int16).tobytes()


def _samples(audio: bytes) -> np.ndarray:
    return np.frombuffer(audio, dtype=np.int16)


def test_zero_gain_is_a_passthrough():
    audio = _pcm([100, -200, 300])
    assert apply_gain(audio, 0.0) is audio


def test_positive_gain_scales_samples():
    scaled = _samples(apply_gain(_pcm([1000, -1000]), 6.0))
    factor = db_to_linear(6.0)
    assert scaled[0] == int(1000 * factor)
    assert scaled[1] == -int(1000 * factor)


def test_clipping_protects_int16_range():
    scaled = _samples(apply_gain(_pcm([30000, -30000]), 12.0))
    assert scaled[0] == 32767
    assert scaled[1] == -32768


def test_negative_gain_attenuates():
    scaled = _samples(apply_gain(_pcm([1000]), -6.0))
    assert abs(int(scaled[0]) - int(1000 * db_to_linear(-6.0))) <= 1


def test_processor_clamps_gain_range():
    processor = AudioGainProcessor(gain_db=999.0)
    assert processor._gain_db == MAX_GAIN_DB
    processor = AudioGainProcessor(gain_db=-999.0)
    assert processor._gain_db == MIN_GAIN_DB
