"""Sarvam AI TTS provider (cloud, WebSocket streaming, Indic voices).

Requires the `sarvam` extra (build with `EXTRAS=sarvam`) and `SARVAM_API_KEY`.
Default voice `shubh` on `bulbul:v3`; other voices include
aditya, ritu, priya, neha, rahul, pooja, rohan, simran, kavya, amit, dev,
ishita, shreya, ratan, varun, manan, sumit, roopa, kabir, aayan.
"""

from __future__ import annotations

from pipecat.services.sarvam.tts import SarvamTTSService

from mai_voice.config import Settings
from mai_voice.processors.text_filters import build_text_filters
from mai_voice.providers._languages import pipecat_language


def create(settings: Settings) -> SarvamTTSService:
    return SarvamTTSService(
        api_key=settings.sarvam_api_key,
        settings=SarvamTTSService.Settings(
            model=settings.sarvam_tts_model,
            voice=settings.sarvam_tts_voice,
            language=pipecat_language(settings.sarvam_language),
        ),
        text_filters=build_text_filters(settings.tts_text_filters),
    )
