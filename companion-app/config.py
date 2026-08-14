"""
Loads/saves the key -> [app paths] mapping. One slot can hold any number of
app paths; on keypress every path assigned to that slot gets launched.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get_apps_for_slot(config: dict, slot: str) -> list:
    return config.get(slot, [])


def add_app_to_slot(config: dict, slot: str, app_path: str) -> dict:
    config.setdefault(slot, [])
    if app_path not in config[slot]:
        config[slot].append(app_path)
    return config


def remove_app_from_slot(config: dict, slot: str, app_path: str) -> dict:
    if slot in config and app_path in config[slot]:
        config[slot].remove(app_path)
    return config
