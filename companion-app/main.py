"""
Entry point. Wires the pieces together:

  Teensy key press -> listener.py (pynput, background thread)
                    -> queue (thread-safe hop back to the GUI's main thread)
                    -> either: normal mode -> config lookup -> launcher.py
                       or:     assign mode -> select/confirm flow below

Assign mode (the "verification system" from the flowchart):
  1. Click "Assign via Key Press..."
  2. Press the physical key you want to assign -> file picker opens,
     choose one or more apps -> they show in amber ("unconfirmed")
  3. Press that SAME key again -> confirmed, saved for real
     Press a DIFFERENT key instead -> cancelled, nothing saved

No firmware changes needed for this -- the physical key already sends a
stable, repeatable code, so "press to select" / "press to confirm" is just
software state built on top of the same listener used at runtime.

Run with the Teensy plugged in and flashed. Without hardware, use the
mouse-driven "Add App..." buttons in each row instead -- both paths write to
the same config.
"""

import queue
import tkinter as tk
from tkinter import filedialog

import config as config_store
from gui import QuickieGUI
from keymap import SLOT_LABELS
from launcher import launch_all
from listener import start_listener

event_queue: "queue.Queue[str]" = queue.Queue()

# Assign-mode state. "idle" = normal runtime behavior (keypress launches
# whatever's assigned). "awaiting_select" = next keypress picks the slot.
# "awaiting_confirm" = next keypress must match, or it cancels.
mode = "idle"
pending_slot = None
pending_paths = []


def on_slot_pressed(slot: str):
    # Runs on the listener's background thread -- keep this fast, and don't
    # touch Tkinter here. Just hand off to the main thread via the queue.
    event_queue.put(slot)


def start_assign(gui):
    global mode, pending_slot, pending_paths
    mode = "awaiting_select"
    pending_slot = None
    pending_paths = []
    gui.set_assign_enabled(False)
    gui.set_status("Assign mode: press the physical key you want to assign...")


def _handle_select(slot, gui):
    global mode, pending_slot, pending_paths

    label = SLOT_LABELS.get(slot, slot)
    paths = filedialog.askopenfilenames(title=f"Choose app(s) for {label}")
    if not paths:
        mode = "idle"
        gui.set_assign_enabled(True)
        gui.set_status("Assign cancelled (no app chosen).")
        return

    pending_slot = slot
    pending_paths = list(paths)
    gui.add_pending(slot, pending_paths)
    mode = "awaiting_confirm"
    gui.set_status(f"Press {label} again to confirm, or press a different key to cancel.")


def _handle_confirm(slot, gui, slots):
    global mode, pending_slot, pending_paths

    if slot == pending_slot:
        for path in pending_paths:
            config_store.add_app_to_slot(slots, slot, path)
        config_store.save_config(current_config)
        gui.confirm_pending(slot)
        gui.set_status(f"Confirmed: {SLOT_LABELS.get(slot, slot)} updated.")
    else:
        gui.cancel_pending(pending_slot)
        gui.set_status("Cancelled -- wrong key pressed. Click 'Assign via Key Press...' to retry.")

    mode = "idle"
    pending_slot = None
    pending_paths = []
    gui.set_assign_enabled(True)


def process_queue(root, gui, get_slots):
    global mode
    try:
        while True:
            slot = event_queue.get_nowait()
            slots = get_slots()

            if mode == "idle":
                apps = config_store.get_apps_for_slot(slots, slot)
                label = SLOT_LABELS.get(slot, slot)
                if apps:
                    gui.set_status(f"{label} -> launching {len(apps)} app(s)")
                    launch_all(apps)
                else:
                    gui.set_status(f"{label} pressed (nothing assigned yet)")
            elif mode == "awaiting_select":
                _handle_select(slot, gui)
            elif mode == "awaiting_confirm":
                _handle_confirm(slot, gui, slots)
    except queue.Empty:
        pass
    root.after(100, process_queue, root, gui, get_slots)


current_config = None  # module-level so _handle_confirm can save it


def main():
    global current_config
    current_config = config_store.load_config()

    root = tk.Tk()

    def get_active_slots():
        return config_store.get_active_slots(current_config)

    def on_change():
        config_store.save_config(current_config)

    def on_profile_change(name):
        config_store.set_active_profile(current_config, name)
        config_store.save_config(current_config)
        gui.reload_slots(config_store.get_active_slots(current_config))

    def on_new_profile(name):
        config_store.add_profile(current_config, name)
        config_store.set_active_profile(current_config, name)
        config_store.save_config(current_config)
        gui.set_profile_list(config_store.list_profiles(current_config), name)
        gui.reload_slots(config_store.get_active_slots(current_config))

    gui = QuickieGUI(
        root,
        get_active_slots(),
        config_store.list_profiles(current_config),
        current_config["active_profile"],
        on_change,
        on_profile_change,
        on_new_profile,
        lambda: start_assign(gui),
    )

    start_listener(on_slot_pressed)

    root.after(100, process_queue, root, gui, get_active_slots)
    root.mainloop()


if __name__ == "__main__":
    main()
