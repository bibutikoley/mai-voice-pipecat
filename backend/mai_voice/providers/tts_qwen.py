"""Qwen3-TTS provider (local, transformers/qwen-tts package).

Generation is non-streaming (one waveform per aggregated sentence), then chunked
into audio frames for playback. On CPU this means seconds of latency per
sentence; Moonshine/Kokoro remain the low-latency defaults.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import numpy as np
from loguru import logger
from pipecat.audio.utils import create_stream_resampler
from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame
from pipecat.services.tts_service import TTSService

from mai_voice.config import Settings
from mai_voice.lifecycle import ReleasesModels
from mai_voice.processors.text_filters import build_text_filters

QWEN_TTS_SAMPLE_RATE = 24000
_AUDIO_CHUNK_SECONDS = 0.02


class QwenTTSService(ReleasesModels, TTSService):
    """Qwen3-TTS CustomVoice synthesis on CPU."""

    _model_attrs = ("_model",)

    def __init__(
        self,
        *,
        model_name: str = "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        speaker: str = "Ryan",
        language: str = "English",
        device: str = "cpu",
        **kwargs,
    ):
        super().__init__(
            sample_rate=QWEN_TTS_SAMPLE_RATE,
            push_start_frame=True,
            push_stop_frames=True,
            **kwargs,
        )
        self._model_name = model_name
        self._speaker = speaker
        self._language = language
        self._device = device
        self._model = None
        self._resampler = create_stream_resampler()

    def _load(self):
        import torch
        from qwen_tts import Qwen3TTSModel

        logger.info(f"Loading Qwen TTS model {self._model_name} ({self._device})...")
        model = Qwen3TTSModel.from_pretrained(
            self._model_name,
            device_map=self._device,
            dtype=torch.float32,
        )
        logger.info("Qwen TTS model loaded")
        return model

    def _generate(self, text: str) -> tuple[np.ndarray, int]:
        if self._model is None:
            self._model = self._load()
        wavs, sample_rate = self._model.generate_custom_voice(
            text=text,
            language=self._language,
            speaker=self._speaker,
        )
        return np.asarray(wavs[0], dtype=np.float32), int(sample_rate)

    async def _keepalive(self, context_id: str, stop: asyncio.Event) -> None:
        """Ping the TTS context while the model generates.

        Pipecat waits `stop_frame_timeout_s` (3s by default) for audio in a
        context before declaring it silent. Qwen TTS is non-streaming and much
        slower than that on CPU, so the context would be torn down mid-generation
        without this heartbeat.
        """
        while not stop.is_set():
            self._refresh_audio_context(context_id)
            try:
                await asyncio.wait_for(stop.wait(), timeout=1.0)
            except TimeoutError:
                continue

    async def run_tts(self, text: str, context_id: str) -> AsyncGenerator[Frame, None]:
        stop = asyncio.Event()
        keepalive = self.create_task(self._keepalive(context_id, stop))
        try:
            await self.start_tts_usage_metrics(text)
            wav, sample_rate = await asyncio.to_thread(self._generate, text)

            audio_int16 = (np.clip(wav, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
            audio_data = await self._resampler.resample(
                audio_int16, sample_rate, self.sample_rate
            )

            await self.stop_ttfb_metrics()
            chunk_bytes = max(2, int(self.sample_rate * _AUDIO_CHUNK_SECONDS) * 2)
            for offset in range(0, len(audio_data), chunk_bytes):
                yield TTSAudioRawFrame(
                    audio=audio_data[offset : offset + chunk_bytes],
                    sample_rate=self.sample_rate,
                    num_channels=1,
                    context_id=context_id,
                )
        except Exception as exc:
            logger.exception("Qwen TTS synthesis failed")
            yield ErrorFrame(error=f"Qwen TTS error: {exc}")
        finally:
            stop.set()
            await self.cancel_task(keepalive)
            await self.stop_ttfb_metrics()


def create(settings: Settings) -> QwenTTSService:
    return QwenTTSService(
        model_name=settings.qwen_tts_model,
        speaker=settings.qwen_tts_speaker,
        language=settings.qwen_tts_language,
        device=settings.qwen_tts_device,
        text_filters=build_text_filters(settings.tts_text_filters),
    )
