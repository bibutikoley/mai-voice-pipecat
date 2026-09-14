"""Unit tests for TTS text filters."""

from __future__ import annotations

import pytest

from mai_voice.config import ConfigError, load_settings
from mai_voice.processors.text_filters import EmojiFilter, build_text_filters


async def test_markdown_filter_strips_formatting():
    (markdown_filter,) = build_text_filters(("markdown",))
    result = await markdown_filter.filter("## Title\n\n**bold** and *italic* and [link](http://x.com)")
    assert "#" not in result
    assert "*" not in result
    assert "Title" in result
    assert "bold" in result
    assert "link" in result


async def test_emoji_filter_removes_emoji_and_tidies_spaces():
    result = await EmojiFilter().filter("Great! 🎤🎧 How can I help?")
    assert "🎤" not in result
    assert "🎧" not in result
    assert "Great!" in result
    assert "How can I help?" in result
    assert "  " not in result


def test_none_disables_filters():
    assert build_text_filters(("none",)) == []
    assert build_text_filters(()) == []


def test_unknown_filter_is_rejected():
    with pytest.raises(ConfigError, match="Unknown TTS text filter"):
        build_text_filters(("shouting",))


def test_settings_parse_filter_list():
    assert load_settings({}).tts_text_filters == ("markdown", "emoji")
    assert load_settings({"TTS_TEXT_FILTERS": "markdown"}).tts_text_filters == ("markdown",)
    assert load_settings({"TTS_TEXT_FILTERS": "none"}).tts_text_filters == ()
