"""
Loads/saves the profile-aware config: a named set of profiles, each holding
its own key/encoder -> [app paths] mapping, plus which profile is active.

    {
      "active_profile": "profile_1",
      "profiles": {
        "profile_1": { "key_1": [...], ..., "encoder_click": [...] },
        "profile_2": { ... }
      }
    }

One slot can hold any number of app paths; on keypress every path assigned
to that slot (in the active profile) gets launched.
"""

import json
import os

from keymap import SLOT_ORDER

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
DEFAULT_PROFILE = "profile_1"


def _empty_slots() -> dict:
    return {slot: [] for slot in SLOT_ORDER}


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


def get_apps_for_slot(slots: dict, slot: str) -> list:
    return slots.get(slot, [])


def add_app_to_slot(slots: dict, slot: str, app_path: str) -> None:
    slots.setdefault(slot, [])
    if app_path not in slots[slot]:
        slots[slot].append(app_path)


def remove_app_from_slot(slots: dict, slot: str, app_path: str) -> None:
    if slot in slots and app_path in slots[slot]:
        slots[slot].remove(app_path)
