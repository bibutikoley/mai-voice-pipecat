"""Unit tests for the model release lifecycle."""

from __future__ import annotations

from mai_voice import lifecycle


class BaseService:
    def __init__(self):
        self.base_cleaned = False

    async def cleanup(self):
        self.base_cleaned = True


class Service(lifecycle.ReleasesModels, BaseService):
    _model_attrs = ("_model",)

    def __init__(self):
        super().__init__()
        self._model = object()


async def test_session_mode_releases_models():
    lifecycle.configure("session")
    service = Service()
    await service.cleanup()
    assert service.base_cleaned is True
    assert service._model is None


async def test_warm_mode_keeps_models():
    lifecycle.configure("warm")
    try:
        service = Service()
        model = service._model
        await service.cleanup()
        assert service.base_cleaned is True
        assert service._model is model
    finally:
        lifecycle.configure("session")
