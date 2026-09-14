"""TTS text filters.

LLMs often answer in markdown, and Kokoro/Piper/Qwen will happily read the
symbols aloud ("asterisk asterisk", "hashtag"). These filters run after text
aggregation, before synthesis, so every TTS provider speaks clean prose.

Configured with `TTS_TEXT_FILTERS` (comma-separated): `markdown`, `emoji`, or
`none` to disable.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from pipecat.utils.text.base_text_filter import BaseTextFilter

_EMOJI_RE = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"  # regional indicators (flags)
    "\U0001f300-\U0001faff"  # symbols, pictographs, emoticons
    "\U00002600-\U000027bf"  # misc symbols, dingbats
    "\U00002b00-\U00002bff"  # arrows, stars
    "\U0000fe0f"             # variation selector
    "\U0000200d"             # zero-width joiner
    "]+"
)

KNOWN_FILTERS = ("markdown", "emoji")


class EmojiFilter(BaseTextFilter):
    """Removes emoji and pictographs from text headed to TTS."""

    async def filter(self, text: str) -> str:
        cleaned = _EMOJI_RE.sub("", text)
        return re.sub(r"[ \t]{2,}", " ", cleaned)


def build_text_filters(names: Iterable[str]) -> list[BaseTextFilter]:
    """Build the configured TTS text filters.

    Args:
        names: Filter names such as ``("markdown", "emoji")``. ``none`` (or an
            empty string) disables filtering.

    Raises:
        ConfigError: If a name is unknown.
    """
    from mai_voice.config import ConfigError

    filters: list[BaseTextFilter] = []
    for name in names:
        key = name.strip().lower()
        if not key or key == "none":
            continue
        if key == "markdown":
            from pipecat.utils.text.markdown_text_filter import MarkdownTextFilter

            filters.append(MarkdownTextFilter())
        elif key == "emoji":
            filters.append(EmojiFilter())
        else:
            raise ConfigError(
                f"Unknown TTS text filter '{name}'. Available: {', '.join(KNOWN_FILTERS)}, none"
            )
    return filters
