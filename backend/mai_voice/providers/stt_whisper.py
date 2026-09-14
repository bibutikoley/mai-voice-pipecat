"""Whisper STT provider (local, faster-whisper). Requires the `whisper` extra."""

from __future__ import annotations

from pipecat.services.whisper.stt import WhisperSTTService
from pipecat.transcriptions.language import Language

from mai_voice.config import Settings
from mai_voice.lifecycle import ReleasesModels


class WhisperLocal(ReleasesModels, WhisperSTTService):
    """Whisper STT that releases its model when the session ends."""

    _model_attrs = ("_model",)


def create(settings: Settings) -> WhisperSTTService:
    return WhisperLocal(
        device="cpu",
        compute_type="int8",
        settings=WhisperLocal.Settings(
            model=settings.whisper_model,
            language=Language.EN,
        ),
    )
