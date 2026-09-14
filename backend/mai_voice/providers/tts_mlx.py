"""MLX-Audio server TTS provider (Apple Silicon host, OpenAI-compatible API).

`mlx_audio.server` returns WAV audio from `/v1/audio/speech` (not raw PCM like
OpenAI), so this provider POSTs the request, decodes the WAV, and streams the
samples downstream as TTS audio frames.

The server binds to 127.0.0.1 on the Mac and is reached through
`host.docker.internal`; it is never exposed to the LAN or the mobile apps.
"""

from __future__ import annotations

import asyncio
import io
from collections.abc import AsyncGenerator

import aiohttp
import numpy as np
import soundfile as sf
from loguru import logger
from pipecat.audio.utils import create_stream_resampler
from pipecat.frames.frames import ErrorFrame, Frame, TTSAudioRawFrame
from pipecat.services.tts_service import TTSService

from mai_voice.config import Settings
from mai_voice.lifecycle import ReleasesModels

MLX_TTS_SAMPLE_RATE = 24000
_AUDIO_CHUNK_SECONDS = 0.02
_REQUEST_TIMEOUT_SECONDS = 180


def wav_to_pcm16(wav_bytes: bytes) -> tuple[bytes, int]:
    """Decode WAV bytes to 16-bit PCM samples and their sample rate."""
    data, sample_rate = sf.read(io.BytesIO(wav_bytes), dtype="float32", always_2d=True)
    mono = data.mean(axis=1) if data.shape[1] > 1 else data[:, 0]
    pcm = (np.clip(mono, -1.0, 1.0) * 32767).astype(np.int16)
    return pcm.tobytes(), int(sample_rate)


class MlxTTSService(ReleasesModels, TTSService):
    """TTS backed by an MLX-Audio HTTP server running natively on the Mac."""

    _model_attrs = ()

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        voice: str,
        **kwargs,
    ):
        super().__init__(
            sample_rate=MLX_TTS_SAMPLE_RATE,
            push_start_frame=True,
            push_stop_frames=True,
            **kwargs,
        )
        self._base_url = base_url.rstrip("/")
        self._model_name = model
        self._voice_name = voice
        self._resampler = create_stream_resampler()

    async def _synthesize(self, text: str) -> bytes:
        payload = {
            "model": self._model_name,
            "input": text,
            "voice": self._voice_name,
            "response_format": "wav",
        }
        timeout = aiohttp.ClientTimeout(total=_REQUEST_TIMEOUT_SECONDS)
        async with (
            aiohttp.ClientSession(timeout=timeout) as session,
            session.post(f"{self._base_url}/v1/audio/speech", json=payload) as response,
        ):
            if response.status != 200:
                body = (await response.text())[:300]
                raise RuntimeError(f"MLX TTS server returned {response.status}: {body}")
            return await response.read()

    async def _keepalive(self, context_id: str, stop: asyncio.Event) -> None:
        """Keep the TTS context alive while the host server synthesizes."""
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
            wav_bytes = await self._synthesize(text)
            pcm, sample_rate = wav_to_pcm16(wav_bytes)
            audio_data = await self._resampler.resample(pcm, sample_rate, self.sample_rate)

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
            logger.exception("MLX TTS synthesis failed")
            yield ErrorFrame(error=f"MLX TTS error: {exc}")
        finally:
            stop.set()
            await self.cancel_task(keepalive)
            await self.stop_ttfb_metrics()


def create(settings: Settings) -> MlxTTSService:
    from mai_voice.processors.text_filters import build_text_filters

    return MlxTTSService(
        base_url=settings.mlx_audio_base_url,
        model=settings.mlx_tts_model,
        voice=settings.mlx_tts_voice,
        text_filters=build_text_filters(settings.tts_text_filters),
    )
