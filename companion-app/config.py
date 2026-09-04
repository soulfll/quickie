"""
Loads/saves the profile-aware config: a named set of profiles, each holding
its own key/encoder -> [action] mapping, plus which profile is active.

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
One slot can hold any number of actions, mixed types included; on keypress
every action assigned to that slot (in the active profile) runs in order.
"""

import json
import os

from keymap import SLOT_ORDER

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
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

    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)

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
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


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
    return str(value)
