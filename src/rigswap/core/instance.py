"""Let installers see that RigSwap is running (Windows).

While RigSwap runs it holds a named mutex. The Windows installer and uninstaller check
for it (Inno Setup's AppMutex) and ask the user to close RigSwap first, instead of
leaving files behind or updating a program that's still running. A running switch
is never cut off. Elsewhere this does nothing.
"""

from __future__ import annotations

import sys

MUTEX_NAME = "RigSwapRunning"
_handle = None


def mark_running() -> None:
    global _handle
    if sys.platform != "win32" or _handle is not None:
        return
    try:
        import ctypes

        # Kept open until the process exits; Windows releases it then.
        _handle = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX_NAME)
    except Exception:
        _handle = None
