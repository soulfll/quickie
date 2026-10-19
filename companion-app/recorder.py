"""
Records a sequence of key presses so it can be replayed later as a "macro"
action (see launcher.py for playback, action_picker.py for the Record dialog).

Each recorded event is a plain dict so it saves straight into config.json:
    {"action": "down"|"up", "delay": <seconds since previous event>,
     "key": "<pynput Key name>"        # for named keys like ctrl, enter
     or "char": "a", "vk": 65}         # for ordinary keys

Only the physical key presses made while recording is switched on are
captured, and they stay on this computer. The Quick-Key's own F13-F20 keys are
deliberately skipped, so a macro can never end up triggering a Quick-Key key.
"""

import time

from pynput import keyboard

from listener import VK_TO_SLOT, get_vk

# Long pauses while recording (thinking, switching windows) would make
# playback crawl, so any gap is capped at this many seconds.
MAX_GAP = 1.5


def encode_key(key) -> dict:
    vk = get_vk(key)
    if isinstance(key, keyboard.Key):
        return {"key": key.name, "vk": vk}
    return {"char": getattr(key, "char", None), "vk": vk}


def decode_key(event: dict):
    """Rebuild a pynput key from a saved event, or None if it can't be."""
    name = event.get("key")
    if name:
        named = getattr(keyboard.Key, name, None)
        if named is not None:
            return named
    char = event.get("char")
    # With Ctrl held, some platforms report a control character instead of
    # the letter -- those aren't safe to replay as text, so use the key code.
    if char and char.isprintable():
        return keyboard.KeyCode.from_char(char)
    vk = event.get("vk")
    if vk is not None:
        return keyboard.KeyCode.from_vk(vk)
    return None


class Recorder:
    def __init__(self):
        self.events = []
        self._last_time = None
        self._held = {}  # identity of each key currently down -> its encoded form
        self._listener = None

    @property
    def recording(self) -> bool:
        return self._listener is not None

    def start(self):
        self.events = []
        self._last_time = None
        self._held = {}
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> list:
        """Stops recording and returns the events. Any key still held down at
        this point gets a release added, so replay never leaves one stuck."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
        for encoded in list(self._held.values()):
            self._add("up", encoded)
        self._held = {}
        return self.events

    def _add(self, action: str, encoded: dict):
        now = time.monotonic()
        delay = 0.0 if self._last_time is None else min(now - self._last_time, MAX_GAP)
        self._last_time = now
        self.events.append({"action": action, "delay": round(delay, 3), **encoded})

    @staticmethod
    def _is_quick_key(key) -> bool:
        return get_vk(key) in VK_TO_SLOT

    def _on_press(self, key):
        if self._is_quick_key(key):
            return
        encoded = encode_key(key)
        ident = repr(key)
        if ident in self._held:  # OS key-repeat while held -- not a new press
            return
        self._held[ident] = encoded
        self._add("down", encoded)

    def _on_release(self, key):
        if self._is_quick_key(key):
            return
        ident = repr(key)
        encoded = self._held.pop(ident, None)
        if encoded is not None:
            self._add("up", encoded)


def macro_summary(events: list) -> str:
    """e.g. '12 keystrokes, 3.4s' for the list label."""
    presses = sum(1 for e in events if e.get("action") == "down")
    seconds = sum(e.get("delay", 0) for e in events)
    return f"{presses} keystrokes, {seconds:.1f}s"
