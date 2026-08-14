"""
Maps the Windows virtual-key codes for F13-F23 to friendly slot names, in the
same order the Teensy firmware assigns them (see src/keys.cpp and
src/encoder.cpp). If the physical wiring order ever changes, this is the only
place that needs to change to match.
"""

# VK_F13 = 0x7C (124) ... VK_F24 = 0x87 (135) on Windows.
VK_TO_SLOT = {
    124: "key_1",
    125: "key_2",
    126: "key_3",
    127: "key_4",
    128: "key_5",
    129: "key_6",
    130: "key_7",
    131: "key_8",
    132: "encoder_cw",
    133: "encoder_ccw",
    134: "encoder_click",
}

# Display order for the GUI.
SLOT_ORDER = [
    "key_1", "key_2", "key_3", "key_4",
    "key_5", "key_6", "key_7", "key_8",
    "encoder_cw", "encoder_ccw", "encoder_click",
]

SLOT_LABELS = {
    "key_1": "Key 1",
    "key_2": "Key 2",
    "key_3": "Key 3",
    "key_4": "Key 4",
    "key_5": "Key 5",
    "key_6": "Key 6",
    "key_7": "Key 7",
    "key_8": "Key 8",
    "encoder_cw": "Encoder: Clockwise",
    "encoder_ccw": "Encoder: Counter-clockwise",
    "encoder_click": "Encoder: Click",
}
