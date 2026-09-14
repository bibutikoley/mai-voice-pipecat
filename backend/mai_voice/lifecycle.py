"""Model memory lifecycle.

Local models (Moonshine, Kokoro, Qwen, Whisper, Piper) are loaded per session and
released when the session ends, so memory does not accumulate while the server
keeps running. `release_memory()` returns freed pages to the OS on glibc systems
(the Linux container) and clears framework allocator caches when present.

`MODEL_LIFECYCLE=warm` skips the explicit release; models are then only reclaimed
when the server process exits.
"""

from __future__ import annotations

import gc
import sys
from typing import Any

from loguru import logger

_mode = "session"


def configure(mode: str) -> None:
    """Set the process-wide lifecycle mode (`session` or `warm`)."""
    global _mode
    if mode not in ("session", "warm"):
        raise ValueError(f"Unknown model lifecycle '{mode}'")
    _mode = mode


def release_on_cleanup() -> bool:
    """Whether services should drop model references when cleaned up."""
    return _mode == "session"


def release_memory() -> None:
    """Run GC and return freed heap pages to the OS where the platform allows it."""
    gc.collect()

    if sys.platform.startswith("linux"):
        try:
            import ctypes

            ctypes.CDLL("libc.so.6").malloc_trim(0)
        except Exception:
            pass

    # Only clear framework allocator caches if torch is already loaded. Never
    # import it here: a fresh import costs hundreds of MB and never unloads.
    torch = sys.modules.get("torch")
    if torch is not None:
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                torch.mps.empty_cache()
        except Exception:
            pass


class ReleasesModels:
    """Mixin that drops model references on cleanup and trims memory.

    Subclasses declare the attribute names that hold loaded models via
    ``_model_attrs``. The mixin must be listed before the pipecat service class
    so ``super().cleanup()`` resolves to the service implementation.
    """

    _model_attrs: tuple[str, ...] = ()

    def _release_models(self) -> list[str]:
        released = []
        for attr in self._model_attrs:
            if getattr(self, attr, None) is not None:
                setattr(self, attr, None)
                released.append(attr)
        if released:
            logger.debug(f"{type(self).__name__}: released {', '.join(released)}")
        return released

    async def cleanup(self) -> None:
        await super().cleanup()  # type: ignore[misc]
        if release_on_cleanup():
            self._release_models()
            release_memory()


def get_attr(obj: Any, name: str, default: Any = None) -> Any:
    """Small helper for tests and diagnostics."""
    return getattr(obj, name, default)
