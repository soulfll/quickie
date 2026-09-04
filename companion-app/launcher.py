"""
Runs one saved action for a slot. Each action is
{"type": "app"|"url"|"text", "value": str} -- see config.py for the model
and action_picker.py for where these get created:

  - "app":  launch the program at that path. The only OS-specific piece --
            "launch an installed app" means something different per OS. On
            Windows this is the real deal; on Mac it's a dev-machine stand-in
            so the pipeline can be exercised before final Windows testing.
  - "url":  open it in the default browser. Uses the stdlib `webbrowser`
            module -- works the same on both OSes, no extra dependency.
  - "text": type it out wherever the cursor currently is, via the same
            pynput library the listener already depends on -- no extra
            dependency there either.
"""

import subprocess
import sys
import webbrowser

from pynput.keyboard import Controller as KeyboardController

_kb = KeyboardController()


def _launch_app(path: str) -> None:
    try:
        if sys.platform == "win32":
            # os.startfile handles .exe, .lnk, and anything with a registered
            # file association -- the same as double-clicking it in Explorer.
            import os
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen([path])
    except Exception as e:
        print(f"[launcher] failed to launch app '{path}': {e}")


def _open_url(url: str) -> None:
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[launcher] failed to open url '{url}': {e}")


def _type_text(text: str) -> None:
    try:
        _kb.type(text)
    except Exception as e:
        print(f"[launcher] failed to type text: {e}")


def run_action(action: dict) -> None:
    action_type = action.get("type", "app")
    value = action.get("value", "")
    if action_type == "app":
        _launch_app(value)
    elif action_type == "url":
        _open_url(value)
    elif action_type == "text":
        _type_text(value)
    else:
        print(f"[launcher] unknown action type: {action_type!r}")


def run_all(actions: list) -> None:
    for action in actions:
        run_action(action)
