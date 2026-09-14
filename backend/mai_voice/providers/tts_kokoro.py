"""Kokoro TTS provider (local, ONNX, CPU)."""

from __future__ import annotations

from pipecat.services.kokoro.tts import KokoroTTSService
from pipecat.transcriptions.language import Language

from mai_voice.config import Settings
from mai_voice.lifecycle import ReleasesModels


class KokoroLocal(ReleasesModels, KokoroTTSService):
    """Kokoro TTS that releases its model when the session ends."""

    _model_attrs = ("_kokoro",)


def create(settings: Settings) -> KokoroTTSService:
    return KokoroLocal(
        settings=KokoroLocal.Settings(
            voice=settings.kokoro_voice,
            language=Language.EN_US,
            speed=1.0,
        )
    )
