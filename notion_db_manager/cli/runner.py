from __future__ import annotations

import asyncio
import sys
from typing import Any, Awaitable, Callable, TypeVar


T = TypeVar("T")


class AsyncCommandRunner:
    """Manages the execution lifecycle of asynchronous commands with clean teardown.

    Ensures that all background IOCP callbacks, transports, and subprocess pipes
    (specifically for Windows ProactorEventLoop and Playwright) are given time to drain
    gracefully before the event loop is closed, preventing BaseSubprocessTransport
    unclosed pipe deallocator exceptions caused by CPython issue python/cpython#83413.
    """

    @classmethod
    def patch_windows_proactor_pipe_cleanup(cls) -> None:
        """Patches known CPython Windows asyncio bugs (python/cpython#83413, #104443)
        where PipeHandle.fileno() raises 'ValueError: I/O operation on closed pipe'
        instead of returning -1, causing BaseSubprocessTransport.__del__ and
        _ProactorBasePipeTransport.__del__ to crash during interpreter GC shutdown."""
        if sys.platform != "win32":
            return

        try:
            from asyncio import windows_utils

            _orig_fileno = getattr(windows_utils.PipeHandle, "fileno", None)
            if _orig_fileno is not None and not getattr(windows_utils.PipeHandle, "_ndm_patched", False):

                def _safe_fileno(self: Any) -> int:
                    if getattr(self, "_handle", None) is None:
                        return -1
                    try:
                        return _orig_fileno(self)
                    except (ValueError, OSError):
                        return -1

                windows_utils.PipeHandle.fileno = _safe_fileno  # type: ignore[method-assign]
                windows_utils.PipeHandle._ndm_patched = True  # type: ignore[attr-defined]
        except Exception:
            pass

        try:
            from asyncio.base_subprocess import BaseSubprocessTransport

            _orig_sub_del = getattr(BaseSubprocessTransport, "__del__", None)
            if _orig_sub_del is not None and not getattr(BaseSubprocessTransport, "_ndm_patched", False):

                def _safe_sub_del(self: Any, *args: Any, **kwargs: Any) -> None:
                    try:
                        _orig_sub_del(self, *args, **kwargs)
                    except (ValueError, OSError):
                        pass

                BaseSubprocessTransport.__del__ = _safe_sub_del  # type: ignore[method-assign]
                BaseSubprocessTransport._ndm_patched = True  # type: ignore[attr-defined]
        except Exception:
            pass

        try:
            from asyncio.proactor_events import _ProactorBasePipeTransport

            _orig_del = getattr(_ProactorBasePipeTransport, "__del__", None)
            if _orig_del is not None and not getattr(_ProactorBasePipeTransport, "_ndm_patched", False):

                def _safe_del(self: Any, *args: Any, **kwargs: Any) -> None:
                    try:
                        _orig_del(self, *args, **kwargs)
                    except (ValueError, OSError):
                        pass

                _ProactorBasePipeTransport.__del__ = _safe_del  # type: ignore[method-assign]
                _ProactorBasePipeTransport._ndm_patched = True  # type: ignore[attr-defined]
        except Exception:
            pass


    @classmethod
    def run(cls, coro_fn: Callable[[], Awaitable[T]]) -> T:
        """Executes an asynchronous workflow inside an asyncio event loop, safely
        draining event loop callbacks before loop teardown."""
        cls.patch_windows_proactor_pipe_cleanup()

        async def _wrapper() -> T:
            try:
                return await coro_fn()
            finally:
                # Yield briefly to allow the ProactorEventLoop to process pending IOCP close notifications
                await asyncio.sleep(0.05)

        return asyncio.run(_wrapper())

