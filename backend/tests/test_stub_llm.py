"""Unit tests for the stub LLM reply logic."""

from __future__ import annotations

from mai_voice.providers.llm_stub import GREETING, StubLLM


class FakeContext:
    def __init__(self, messages):
        self.messages = messages


def test_echoes_last_user_message():
    stub = StubLLM()
    context = FakeContext(
        [
            {"role": "developer", "content": "greet"},
            {"role": "user", "content": "what's the weather?"},
        ]
    )
    assert "what's the weather?" in stub._reply(context)


def test_greets_when_no_user_message():
    stub = StubLLM()
    context = FakeContext([{"role": "developer", "content": "greet"}])
    assert stub._reply(context) == GREETING


def test_handles_list_content():
    stub = StubLLM()
    context = FakeContext(
        [
            {
                "role": "user",
                "content": [{"type": "text", "text": "hello from parts"}],
            }
        ]
    )
    assert "hello from parts" in stub._reply(context)
