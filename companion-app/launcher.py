"""
The only OS-specific part of the companion app. Everything else (listener,
config, GUI) runs the same on Mac and Windows; this is the one function that
has to actually differ, because "launch an installed app" means something
different per OS.

On Windows this is the real deal. On Mac it's a stand-in so you can exercise
the full pipeline (key event -> look up slot -> launch apps) during
development, using Mac apps instead of .exe paths, before final testing on
real Windows hardware.
"""

import subprocess
import sys


def launch_app(path: str) -> None:
    try:
        if sys.platform == "win32":
            # os.startfile handles .exe, .lnk, and anything with a registered
            # file association -- the same as double-clicking it in Explorer.
            import os
            os.startfile(path)
        elif sys.platform == "darwin":
            # Dev-machine stand-in: `open` launches .app bundles (and
            # regular files via their default app).
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen([path])
    except Exception as e:
        print(f"[launcher] failed to launch '{path}': {e}")


def launch_all(paths: list) -> None:
    for path in paths:
        launch_app(path)
