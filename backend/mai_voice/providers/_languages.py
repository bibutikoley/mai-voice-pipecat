"""Language helpers shared by providers."""

from __future__ import annotations

from pipecat.transcriptions.language import Language

from mai_voice.config import ConfigError


def pipecat_language(value: str) -> Language:
    """Resolve an ISO language code (e.g. ``en-IN``) to a pipecat Language."""
    try:
        return Language(value)
    except ValueError as exc:
        raise ConfigError(
            f"Unsupported language '{value}'. Use an ISO code such as 'en-IN' or 'hi-IN'."
        ) from exc
