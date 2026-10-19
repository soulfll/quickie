"""
Runs one saved action for a slot. Each action is
{"type": "app"|"url"|"text"|"macro", "value": ...} -- see config.py for the
model and action_picker.py for where these get created:

  - "app":   launch the program at that path. The only OS-specific piece --
             "launch an installed app" means something different per OS. On
             Windows this is the real deal; on Mac it's a dev-machine stand-in
             so the pipeline can be exercised before final Windows testing.
  - "url":   open it in the default browser. Uses the stdlib `webbrowser`
             module -- works the same on both OSes, no extra dependency.
  - "text":  type it out wherever the cursor currently is, via the same
             pynput library the listener already depends on -- no extra
             dependency there either.
  - "macro": replay a recorded list of key down/up events (see recorder.py)
             with the original timing. Best replayed on the same OS it was
             recorded on, since named keys like Cmd/Win differ between them.
"""

import subprocess
import sys
import threading
import time
import webbrowser

from pynput.keyboard import Controller as KeyboardController

from recorder import decode_key

_kb = KeyboardController()

# Playback can take seconds (macros keep their original pauses), so only one
# run happens at a time -- a second press mid-playback is ignored instead of
# piling keystrokes on top of the first.
_run_lock = threading.Lock()


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


def _play_macro(events: list) -> None:
    pressed = []
    try:
        for event in events:
            time.sleep(event.get("delay", 0))
            key = decode_key(event)
            if key is None:
                continue
            if event.get("action") == "down":
                _kb.press(key)
                pressed.append(key)
            else:
                _kb.release(key)
                if key in pressed:
                    pressed.remove(key)
    except Exception as e:
        print(f"[launcher] macro playback failed: {e}")
    finally:
        # Never leave a modifier stuck down if playback stops early.
        for key in pressed:
            try:
                _kb.release(key)
            except Exception:
                pass


def run_action(action: dict) -> None:
    action_type = action.get("type", "app")
    value = action.get("value", "")
    if action_type == "app":
        _launch_app(value)
    elif action_type == "url":
        _open_url(value)
    elif action_type == "text":
        _type_text(value)
    elif action_type == "macro":
        _play_macro(value)
    else:
        print(f"[launcher] unknown action type: {action_type!r}")


def run_all(actions: list) -> None:
    """Runs every action for a slot in order. Blocks until they finish, so
    callers should run this off the GUI thread (see main.py)."""
    if not _run_lock.acquire(blocking=False):
        print("[launcher] still running the previous key press -- ignored")
        return
    try:
        for action in actions:
            run_action(action)
    finally:
        _run_lock.release()
