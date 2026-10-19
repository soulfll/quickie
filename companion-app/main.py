"""
Entry point. Wires the pieces together:

  Teensy key press -> listener.py (pynput, background thread)
                    -> queue (thread-safe hop back to the GUI's main thread)
                    -> either: normal mode -> config lookup -> launcher.py
                       or:     assign mode -> select/confirm flow below

Assign mode (the "verification system" from the flowchart):
  1. Click "Assign via Key Press..."
  2. Press the physical key you want to assign -> the action-type popup
     opens (App / Website / Text Snippet, see action_picker.py) -> pick one
     and fill it in -> it shows in amber ("unconfirmed")
  3. Press that SAME key again -> confirmed, saved for real
     Press a DIFFERENT key instead -> cancelled, nothing saved

No firmware changes needed for this -- the physical key already sends a
stable, repeatable code, so "press to select" / "press to confirm" is just
software state built on top of the same listener used at runtime.

Run with the Teensy plugged in and flashed. Without hardware, use the
mouse-driven "Add..." buttons in each row instead -- both paths write to
the same config.
"""

import queue
import threading
import tkinter as tk

import config as config_store
from action_picker import prompt_for_actions
from device_link import DeviceLink
from gui import QuickKeyGUI
from keymap import SLOT_LABELS
from launcher import run_all
from listener import start_listener
from volume_sync import VolumeWatcher, get_volume

event_queue: "queue.Queue[str]" = queue.Queue()

# Assign-mode state. "idle" = normal runtime behavior (keypress runs
# whatever's assigned). "awaiting_select" = next keypress picks the slot.
# "awaiting_confirm" = next keypress must match, or it cancels.
mode = "idle"
pending_slot = None
pending_actions = []


def on_slot_pressed(slot: str):
    # Runs on the listener's background thread -- keep this fast, and don't
    # touch Tkinter here. Just hand off to the main thread via the queue.
    event_queue.put(slot)


def _one_line(actions):
    """All of a key's actions as one short line, e.g. 'Word, Outlook'."""
    return ", ".join(config_store.action_short_name(a) for a in actions)


def start_assign(gui):
    global mode, pending_slot, pending_actions
    mode = "awaiting_select"
    pending_slot = None
    pending_actions = []
    gui.set_assign_enabled(False)
    gui.set_status("Assign mode: press the physical key you want to assign...")
    link.show("Assign a key", ["Press the key you", "want to set"], sticky=True)


def _handle_select(slot, gui):
    global mode, pending_slot, pending_actions

    label = SLOT_LABELS.get(slot, slot)
    link.show(label, ["Choose what it does", "on your computer"], sticky=True)
    actions = prompt_for_actions(gui.root)
    if not actions:
        mode = "idle"
        gui.set_assign_enabled(True)
        gui.set_status("Assign cancelled.")
        link.show("Cancelled", ["Nothing was chosen"])
        return

    pending_slot = slot
    pending_actions = actions
    gui.add_pending(slot, pending_actions)
    mode = "awaiting_confirm"
    gui.set_status(f"Press {label} again to confirm, or press a different key to cancel.")
    link.show(label, [_one_line(actions), "Press this key again", "to confirm"], sticky=True)


def _handle_confirm(slot, gui, slots):
    global mode, pending_slot, pending_actions

    if slot == pending_slot:
        link.show("Saved!", [SLOT_LABELS.get(slot, slot), _one_line(pending_actions)])
        config_store.add_actions_to_slot(slots, slot, pending_actions)
        config_store.save_config(current_config)
        gui.confirm_pending(slot)
        gui.set_status(f"Confirmed: {SLOT_LABELS.get(slot, slot)} updated.")
    else:
        gui.cancel_pending(pending_slot)
        gui.set_status("Cancelled -- wrong key pressed. Click 'Assign via Key Press...' to retry.")
        link.show("Cancelled", ["Wrong key pressed"])

    mode = "idle"
    pending_slot = None
    pending_actions = []
    gui.set_assign_enabled(True)


def process_queue(root, gui, get_slots):
    global mode
    try:
        while True:
            slot = event_queue.get_nowait()
            slots = get_slots()

            if mode == "idle":
                actions = config_store.get_actions_for_slot(slots, slot)
                label = SLOT_LABELS.get(slot, slot)
                link.show(label, config_store.summarize_actions(actions))
                if actions:
                    gui.set_status(f"{label} -> running {len(actions)} action(s)")
                    # Off the GUI thread: macros keep their pauses, and a
                    # blocking replay would freeze the window.
                    threading.Thread(target=run_all, args=(actions,), daemon=True).start()
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
link = DeviceLink()    # sends the profile name to the Quick-Key's screen
# Reads the real system volume after a volume key and shows it on the screen.
volume_watcher = VolumeWatcher(link.show_volume)


def main():
    global current_config
    current_config = config_store.load_config()

    root = tk.Tk()

    def get_active_slots():
        return config_store.get_active_slots(current_config)

    def on_change():
        config_store.save_config(current_config)

    def sync_link():
        """Push the active profile to the device's screen."""
        link.set_profile(current_config["active_profile"])

    def on_profile_change(name):
        config_store.set_active_profile(current_config, name)
        config_store.save_config(current_config)
        gui.reload_slots(config_store.get_active_slots(current_config))
        sync_link()

    def on_new_profile(name):
        config_store.add_profile(current_config, name)
        config_store.set_active_profile(current_config, name)
        config_store.save_config(current_config)
        gui.set_profile_list(config_store.list_profiles(current_config), name)
        gui.reload_slots(config_store.get_active_slots(current_config))
        sync_link()

    gui = QuickKeyGUI(
        root,
        get_active_slots(),
        config_store.list_profiles(current_config),
        current_config["active_profile"],
        on_change,
        on_profile_change,
        on_new_profile,
        lambda: start_assign(gui),
    )

    start_listener(on_slot_pressed, on_volume_key=volume_watcher.notify)
    sync_link()
    link.start()
    # Load the audio library now so the very first volume click isn't slow.
    threading.Thread(target=get_volume, daemon=True).start()

    root.after(100, process_queue, root, gui, get_active_slots)
    root.mainloop()


if __name__ == "__main__":
    main()
