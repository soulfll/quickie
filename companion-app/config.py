"""
Loads/saves the profile-aware config: a named set of profiles, each holding
its own key -> [action] mapping, plus which profile is active.

    {
      "active_profile": "profile_1",
      "profiles": {
        "profile_1": { "key_1": [ {"type": "app", "value": "..."} ], ... },
        "profile_2": { ... }
      }
    }

Each slot holds a list of *actions*, not just app paths -- see
action_picker.py for where these get created. An action is:
    {"type": "app",  "value": "<path to .exe/.app>"}
    {"type": "url",  "value": "<https://...>"}
    {"type": "text", "value": "<snippet to type out>"}
    {"type": "macro", "value": [<recorded key down/up events>]}  (see recorder.py)
One slot can hold any number of actions, mixed types included; on keypress
every action assigned to that slot (in the active profile) runs in order.
"""

import json
import os
import sys
from urllib.parse import urlparse

from keymap import SLOT_ORDER


def data_dir() -> str:
    """Where Quick-Key keeps the user's settings (and its error log).

    Running from source (a developer): next to the code, as it always was.
    Running as the installed .exe: the code lives in a temporary folder that is
    deleted when the app closes, and in Program Files it wouldn't be writable
    anyway -- so settings go in the user's own app-data folder, which survives
    restarts, upgrades and reinstalls."""
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "Quick-Key")
        os.makedirs(folder, exist_ok=True)
        return folder
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(data_dir(), "config.json")
DEFAULT_PROFILE = "profile_1"


def _empty_slots() -> dict:
    return {slot: [] for slot in SLOT_ORDER}


def _migrate_action(item) -> dict:
    """Configs saved before action types existed just stored a plain path
    string per entry. Upgrade those in place to the {"type": "app", ...}
    shape so old assignments keep working without redoing them by hand."""
    if isinstance(item, str):
        return {"type": "app", "value": item}
    return item


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {
            "active_profile": DEFAULT_PROFILE,
            "profiles": {DEFAULT_PROFILE: _empty_slots()},
        }

    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("config is not a JSON object")
    except (ValueError, OSError) as e:
        # A damaged settings file must not stop the app from opening (the
        # installed app has no console to show an error in). Keep the bad file
        # for inspection and start fresh.
        print(f"[config] couldn't read {CONFIG_PATH}: {e}")
        try:
            os.replace(CONFIG_PATH, CONFIG_PATH + ".broken")
        except OSError:
            pass
        return {
            "active_profile": DEFAULT_PROFILE,
            "profiles": {DEFAULT_PROFILE: _empty_slots()},
        }

    # Defensive defaults in case config.json was hand-edited or is stale.
    data.setdefault("profiles", {})
    data.setdefault("active_profile", DEFAULT_PROFILE)
    if data["active_profile"] not in data["profiles"]:
        data["profiles"].setdefault(data["active_profile"], _empty_slots())
    for slots in data["profiles"].values():
        for slot in SLOT_ORDER:
            slots.setdefault(slot, [])
            slots[slot] = [_migrate_action(a) for a in slots[slot]]

    return data


def save_config(config: dict) -> None:
    # Write to a side file and swap it in, so a crash or power cut mid-save
    # can never leave a half-written config behind.
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(config, f, indent=2)
    os.replace(tmp, CONFIG_PATH)


def list_profiles(config: dict) -> list:
    return list(config["profiles"].keys())


def get_active_slots(config: dict) -> dict:
    """Returns the *live* slot dict for the active profile -- mutating it
    mutates config in place, since it's the same dict, not a copy."""
    return config["profiles"][config["active_profile"]]


def set_active_profile(config: dict, name: str) -> None:
    config["profiles"].setdefault(name, _empty_slots())
    config["active_profile"] = name


def add_profile(config: dict, name: str) -> None:
    config["profiles"].setdefault(name, _empty_slots())


def get_actions_for_slot(slots: dict, slot: str) -> list:
    return slots.get(slot, [])


def add_actions_to_slot(slots: dict, slot: str, actions: list) -> None:
    slots.setdefault(slot, [])
    for action in actions:
        if action not in slots[slot]:
            slots[slot].append(action)


def remove_action_from_slot(slots: dict, slot: str, action: dict) -> None:
    if slot in slots and action in slots[slot]:
        slots[slot].remove(action)


def action_label(action: dict) -> str:
    """Short, scannable one-line label for a list row."""
    action_type = action.get("type", "app")
    value = action.get("value", "")
    if action_type == "app":
        return f"[App] {value}"
    elif action_type == "url":
        return f"[Web] {value}"
    elif action_type == "text":
        preview = value.replace("\n", " ")
        if len(preview) > 40:
            preview = preview[:40] + "…"
        return f"[Text] {preview}"
    elif action_type == "macro":
        from recorder import macro_summary  # local import: recorder pulls in pynput
        return f"[Macro] {macro_summary(value)}"
    return str(value)


def action_short_name(action: dict) -> str:
    """A few words that fit on the Quick-Key's small screen."""
    action_type = action.get("type", "app")
    value = action.get("value", "")
    if action_type == "app":
        base = os.path.basename(str(value).rstrip("/\\"))
        return os.path.splitext(base)[0] or base        # "Word.app" / "Word.lnk" -> "Word"
    if action_type == "url":
        host = urlparse(value).netloc or value
        return host[4:] if host.startswith("www.") else host
    if action_type == "text":
        preview = " ".join(str(value).split())
        return f'"{preview[:22]}"' + ("..." if len(preview) > 22 else "")
    if action_type == "macro":
        presses = sum(1 for e in value if e.get("action") == "down")
        return f"Macro ({presses} keys)"
    return str(value)


def summarize_actions(actions: list, max_lines: int = 3) -> list:
    """One short line per action, for the screen. More than fit are folded
    into a final '+N more'."""
    names = [action_short_name(a) for a in actions]
    if not names:
        return ["Nothing assigned yet"]
    if len(names) <= max_lines:
        return names
    return names[:max_lines - 1] + [f"+{len(names) - (max_lines - 1)} more"]
