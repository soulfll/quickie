"""
Listens globally for the F13-F23 keycodes the Teensy sends and fires a
callback with the friendly slot name (see keymap.py). Runs in a background
thread so it doesn't block the GUI's main loop.
"""

import sys

from pynput import keyboard

from keymap import MAC_VK_TO_SLOT, WIN_VK_TO_SLOT

VK_TO_SLOT = WIN_VK_TO_SLOT if sys.platform == "win32" else MAC_VK_TO_SLOT


def _get_vk(key):
    """pynput represents these two different ways depending on platform:
    - Windows: a plain KeyCode with `.vk` set directly.
    - macOS: a named Key enum member (e.g. Key.f13) whose vk is nested one
      level deeper, at `.value.vk`.
    Check both so the same code works on either.
    """
    vk = getattr(key, "vk", None)
    if vk is not None:
        return vk
    value = getattr(key, "value", None)
    return getattr(value, "vk", None)


def start_listener(on_slot_pressed):
    """on_slot_pressed(slot_name: str) is called once per key-down."""

    def on_press(key):
        vk = _get_vk(key)
        if vk in VK_TO_SLOT:
            on_slot_pressed(VK_TO_SLOT[vk])

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener
