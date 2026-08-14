"""
Listens globally for the F13-F23 keycodes the Teensy sends and fires a
callback with the friendly slot name (see keymap.py). Runs in a background
thread so it doesn't block the GUI's main loop.
"""

from pynput import keyboard

from keymap import VK_TO_SLOT


def start_listener(on_slot_pressed):
    """on_slot_pressed(slot_name: str) is called once per key-down."""

    def on_press(key):
        vk = getattr(key, "vk", None)
        if vk in VK_TO_SLOT:
            on_slot_pressed(VK_TO_SLOT[vk])

    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    return listener
