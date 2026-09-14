"""mai-voice Pipecat server entrypoint.

Runs the Pipecat development runner with the SmallWebRTC transport. Everything
server-side runs in Docker; this file is the container entrypoint.
"""

from __future__ import annotations

from dotenv import load_dotenv
from loguru import logger
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import TransportParams

from mai_voice.config import load_settings
from mai_voice.lifecycle import configure
from mai_voice.pipeline import run_bot


async def bot(runner_args: RunnerArguments):
    """Session entrypoint called by the Pipecat runner for every connection."""
    settings = load_settings()
    configure(settings.model_lifecycle)

    transport_params = {
        "webrtc": lambda: TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
        ),
    }

    transport = await create_transport(runner_args, transport_params)
    await run_bot(transport, settings, handle_sigint=runner_args.handle_sigint)


if __name__ == "__main__":
    load_dotenv(override=False)
    logger.info("Starting mai-voice server")

    from pipecat.runner.run import main

    main()
