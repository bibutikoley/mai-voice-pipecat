"""MLX-Audio server STT provider (Apple Silicon host, OpenAI-compatible API).

Models run natively on the Mac with Metal/MLX behind the `mlx_audio.server`
process started with `make stt-server` (port 8001), which binds to 127.0.0.1
only. The container reaches it via `host.docker.internal`; phones on the LAN
cannot.
"""

from __future__ import annotations

from pipecat.services.openai.stt import OpenAISTTService
from pipecat.transcriptions.language import Language

from mai_voice.config import Settings

# The server ignores auth; the OpenAI SDK just requires a non-empty key.
_FAKE_KEY = "mlx-audio"


def create(settings: Settings) -> OpenAISTTService:
    return OpenAISTTService(
        api_key=_FAKE_KEY,
        base_url=f"{settings.mlx_stt_base_url.rstrip('/')}/v1",
        model=settings.mlx_stt_model,
        language=Language.EN,
        # The local server loads model weights on first request, which can take
        # longer than the cloud default.
        ttfs_p99_latency=None,
    )


def create_whisper_compatible(settings: Settings) -> OpenAISTTService:
    """Alias kept for symmetry with other providers."""
    return create(settings)
