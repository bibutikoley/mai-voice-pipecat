"""Pipeline assembly: transport -> VAD/STT -> LLM -> TTS -> transport.

Services are created inside the session function (not at import time) so the
model lifecycle is bound to the session: on disconnect the pipeline cancels and
each service releases its model (see `mai_voice.lifecycle`).
"""

from __future__ import annotations

from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMRunFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.transports.base_transport import BaseTransport

from mai_voice.config import Settings
from mai_voice.providers import create_llm, create_stt, create_tts

GREETING_PROMPT = (
    "Greet the user warmly in one short sentence and ask how you can help."
)


async def run_bot(transport: BaseTransport, settings: Settings, handle_sigint: bool):
    """Build and run one voice session on the given transport."""
    logger.info(
        "Starting session: "
        f"stt={settings.stt_provider} tts={settings.tts_provider} "
        f"llm={settings.llm_mode} lifecycle={settings.model_lifecycle}"
    )

    context = LLMContext()
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(vad_analyzer=SileroVADAnalyzer()),
    )

    stt = create_stt(settings)
    tts = create_tts(settings)
    llm = create_llm(settings)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(_transport, _client):
        logger.info("Client connected")
        context.add_message({"role": "developer", "content": GREETING_PROMPT})
        await task.queue_frames([LLMRunFrame()])

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(_transport, _client):
        logger.info("Client disconnected")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=handle_sigint)
    await runner.run(task)
