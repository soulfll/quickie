"""
Entry point. Wires the pieces together:

  Teensy key press -> listener.py (pynput, background thread)
                    -> queue (thread-safe hop back to the GUI's main thread)
                    -> config.py lookup (slot -> [app paths])
                    -> launcher.py (actually opens them)
                    -> gui.py status label, for visible confirmation

Run with the Teensy plugged in and flashed; without it, use the "Simulate
key press" test buttons in the console (see bottom of this file) so you can
test the whole pipeline without hardware.
"""

import queue
import tkinter as tk

import config as config_store
from gui import QuickieGUI
from keymap import SLOT_LABELS
from launcher import launch_all
from listener import start_listener

event_queue: "queue.Queue[str]" = queue.Queue()


def on_slot_pressed(slot: str):
    # Called from the listener's background thread -- keep this fast and
    # thread-safe. Actually launching apps is fine here; touching the GUI
    # is not, so that goes through the queue instead.
    event_queue.put(slot)


def process_queue(root, gui, config):
    try:
        while True:
            slot = event_queue.get_nowait()
            apps = config.get(slot, [])
            label = SLOT_LABELS.get(slot, slot)
            if apps:
                gui.set_status(f"{label} -> launching {len(apps)} app(s)")
                launch_all(apps)
            else:
                gui.set_status(f"{label} pressed (nothing assigned yet)")
    except queue.Empty:
        pass
    root.after(100, process_queue, root, gui, config)


def main():
    config = config_store.load_config()

    root = tk.Tk()

    def on_change(slot, updated_config):
        config_store.save_config(updated_config)

    gui = QuickieGUI(root, config, on_change)

    start_listener(on_slot_pressed)

    root.after(100, process_queue, root, gui, config)
    root.mainloop()


if __name__ == "__main__":
    main()
