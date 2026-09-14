"""Output audio gain stage.

Inserted after the TTS service so every provider benefits. Local TTS output is
noticeably quieter than typical assistant speech (measured around -33 dBFS RMS
with Kokoro), so `TTS_GAIN_DB` raises it with clipping protection.
"""

from __future__ import annotations

import numpy as np
from loguru import logger
from pipecat.frames.frames import Frame, OutputAudioRawFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

MAX_GAIN_DB = 24.0
MIN_GAIN_DB = -24.0


def db_to_linear(gain_db: float) -> float:
    """Convert decibels to a linear multiplier."""
    return float(10.0 ** (gain_db / 20.0))


def apply_gain(audio: bytes, gain_db: float) -> bytes:
    """Scale 16-bit PCM audio by `gain_db`, clamping to the int16 range."""
    if gain_db == 0.0 or not audio:
        return audio

    samples = np.frombuffer(audio, dtype=np.int16)
    if samples.size == 0:
        return audio

    scaled = samples.astype(np.float32) * db_to_linear(gain_db)
    np.clip(scaled, -32768.0, 32767.0, out=scaled)
    return scaled.astype(np.int16).tobytes()


class AudioGainProcessor(FrameProcessor):
    """Applies a fixed gain to output audio frames."""

    def __init__(self, gain_db: float = 0.0, **kwargs):
        super().__init__(**kwargs)
        self._gain_db = max(MIN_GAIN_DB, min(MAX_GAIN_DB, float(gain_db)))
        if self._gain_db:
            logger.debug(f"Audio gain: {self._gain_db:+.1f} dB")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, OutputAudioRawFrame) and self._gain_db:
            frame.audio = apply_gain(frame.audio, self._gain_db)
            frame.num_frames = int(len(frame.audio) / (frame.num_channels * 2))

        await self.push_frame(frame, direction)
