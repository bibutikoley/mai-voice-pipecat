"""Stub LLM: canned replies with no model or API key.

Keeps the full voice loop usable (mic -> STT -> reply -> TTS) before the real
LLM endpoint is configured. It consumes `LLMContextFrame`s like an LLM service
would, emits LLM text frames, and lets the pipeline's assistant aggregator
record the reply in context.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from pipecat.frames.frames import (
    Frame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMTextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from mai_voice.config import Settings

GREETING = (
    "Hi, I'm the mai-voice assistant. I can hear you and I'm running with a stub "
    "language model, so my replies are canned for now."
)


class StubLLM(FrameProcessor):
    """Canned-response stand-in for a real LLM."""

    def __init__(self, greeting: str = GREETING, **kwargs):
        super().__init__(**kwargs)
        self._greeting = greeting

    @staticmethod
    def _last_user_text(context: Any) -> str | None:
        messages = getattr(context, "messages", None) or []
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                parts = [
                    part.get("text")
                    for part in content
                    if isinstance(part, dict) and isinstance(part.get("text"), str)
                ]
                text = " ".join(p for p in parts if p).strip()
                if text:
                    return text
        return None

    def _reply(self, context: Any) -> str:
        user_text = self._last_user_text(context)
        if not user_text:
            return self._greeting
        return f"Stub reply. You said: {user_text}"

    async def _emit(self, text: str):
        await self.push_frame(LLMFullResponseStartFrame())
        await self.push_frame(LLMTextFrame(text))
        await self.push_frame(LLMFullResponseEndFrame())

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMContextFrame):
            reply = self._reply(frame.context)
            logger.debug(f"Stub LLM replying: {reply!r}")
            await self._emit(reply)
            return

        await self.push_frame(frame, direction)


def create(settings: Settings) -> StubLLM:
    return StubLLM()
