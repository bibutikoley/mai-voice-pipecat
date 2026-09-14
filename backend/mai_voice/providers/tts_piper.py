"""Piper TTS provider (local). Requires the `piper` extra."""

from __future__ import annotations

from pipecat.services.piper.tts import PiperTTSService

from mai_voice.config import Settings
from mai_voice.lifecycle import ReleasesModels
from mai_voice.processors.text_filters import build_text_filters


class PiperLocal(ReleasesModels, PiperTTSService):
    """Piper TTS that releases its voice model when the session ends."""

    _model_attrs = ("_voice",)


def create(settings: Settings) -> PiperTTSService:
    return PiperLocal(
        settings=PiperLocal.Settings(voice=settings.piper_voice),
        text_filters=build_text_filters(settings.tts_text_filters),
    )
