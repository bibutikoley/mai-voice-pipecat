"""Moonshine STT provider (local, ONNX, CPU)."""

from __future__ import annotations

from pipecat.services.moonshine.stt import MoonshineSTTService
from pipecat.transcriptions.language import Language

from mai_voice.config import Settings
from mai_voice.lifecycle import ReleasesModels


class MoonshineLocal(ReleasesModels, MoonshineSTTService):
    """Moonshine STT that releases its transcriber when the session ends."""

    _model_attrs = ("_transcriber",)


def create(settings: Settings) -> MoonshineSTTService:
    return MoonshineLocal(
        settings=MoonshineLocal.Settings(
            model=settings.moonshine_model,
            language=Language.EN,
        )
    )
