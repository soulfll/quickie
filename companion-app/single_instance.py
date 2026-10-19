"""
Makes sure only one copy of Quick-Key runs at a time.

Two copies would both open the Quick-Key's serial port and both react to every
key press (so each key would run its actions twice), and they fight over the
port, dropping updates to the screen. It is also an easy mistake to make: on
macOS the terminal prompt comes back while the app keeps running, so it looks
like nothing happened and people launch it again.

Uses an operating-system file lock, which is released automatically if the app
crashes or is killed, so a stale lock can never lock you out.
"""

import os
import sys
import tempfile

LOCK_PATH = os.path.join(tempfile.gettempdir(), "quick-key-app.lock")
_handle = None   # kept open for the life of the process; closing it would release the lock


def acquire() -> bool:
    """True if we are the only copy (and now hold the lock); False if another
    copy is already running."""
    global _handle
    _handle = open(LOCK_PATH, "a+")
    try:
        if sys.platform == "win32":
            import msvcrt
            _handle.seek(0)
            msvcrt.locking(_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        _handle.close()
        _handle = None
        return False
    return True
