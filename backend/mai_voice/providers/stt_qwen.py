"""Qwen3-ASR STT provider (local, transformers backend).

The official `qwen-asr` package is loaded lazily on first transcription so the
model only enters memory when a session actually needs it. Segmented pipeline
(the model transcribes complete VAD segments) — the vLLM streaming backend needs
a CUDA GPU and is out of scope for the default CPU container.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import numpy as np
from loguru import logger
from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.stt_service import SegmentedSTTService
from pipecat.utils.time import time_now_iso8601

from mai_voice.config import Settings
from mai_voice.lifecycle import ReleasesModels

QWEN_ASR_SAMPLE_RATE = 16000


class QwenASRService(ReleasesModels, SegmentedSTTService):
    """Qwen3-ASR transcription using the transformers backend on CPU."""

    _model_attrs = ("_model",)

    def __init__(
        self,
        *,
        model_name: str = "Qwen/Qwen3-ASR-0.6B",
        language: str = "English",
        device: str = "cpu",
        **kwargs,
    ):
        super().__init__(sample_rate=QWEN_ASR_SAMPLE_RATE, **kwargs)
        self._model_name = model_name
        self._language = language
        self._device = device
        self._model = None

    @property
    def wants_wav_segments(self) -> bool:
        """Qwen reads raw 16-bit PCM directly."""
        return False

    def _load(self):
        import torch
        from qwen_asr import Qwen3ASRModel

        logger.info(f"Loading Qwen ASR model {self._model_name} ({self._device})...")
        model = Qwen3ASRModel.from_pretrained(
            self._model_name,
            dtype=torch.float32,
            device_map=self._device,
        )
        logger.info("Qwen ASR model loaded")
        return model

    def _ensure_model(self):
        if self._model is None:
            self._model = self._load()
        return self._model

    def _transcribe(self, audio_float: np.ndarray) -> str:
        model = self._ensure_model()
        results = model.transcribe(
            audio=(audio_float, QWEN_ASR_SAMPLE_RATE),
            language=self._language,
        )
        if not results:
            return ""
        return (results[0].text or "").strip()

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        await self.start_processing_metrics()
        try:
            audio_float = np.frombuffer(audio, dtype=np.int16).astype(np.float32) / 32768.0
            text = await asyncio.to_thread(self._transcribe, audio_float)
            await self.stop_processing_metrics()
            if text:
                logger.debug(f"Qwen ASR transcription: [{text}]")
                yield TranscriptionFrame(text, self._user_id, time_now_iso8601(), None)
        except Exception as exc:
            logger.exception("Qwen ASR transcription failed")
            yield ErrorFrame(error=f"Qwen ASR error: {exc}")


def create(settings: Settings) -> QwenASRService:
    return QwenASRService(
        model_name=settings.qwen_asr_model,
        language=settings.qwen_asr_language,
        device=settings.qwen_asr_device,
    )
