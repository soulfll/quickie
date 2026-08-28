"""
Maps a platform's virtual-key numbers for F13-F23 to friendly slot names, in
the same order the Teensy firmware assigns them (see src/keys.cpp and
src/encoder.cpp). If the physical wiring order ever changes, this is the only
place that needs to change to match.

Windows and macOS use *completely different* numbers for the same physical
key, so there are two tables. listener.py picks the right one at runtime via
sys.platform. The Windows table is what matters for the real product; the
macOS table exists purely so this can be dev-tested on a Mac before hardware
ever touches a Windows machine.
"""

# --- Windows -----------------------------------------------------------
# VK_F13 = 0x7C (124) ... VK_F24 = 0x87 (135).
WIN_VK_TO_SLOT = {
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

# --- macOS ---------------------------------------------------------------
# Apple's kVK_F13..kVK_F20 (from Carbon HIToolbox/Events.h), confirmed against
# a real key_1 press (F13 -> 105) on 2026-08-28. Mac keyboards don't have
# physical F21-F24, so there is no standard keycode for the encoder's 3
# actions (F21/F22/F23) -- those can't be dev-tested on Mac via this path.
# That's fine for now since the encoder isn't wired yet either; revisit when
# real Windows testing starts.
MAC_VK_TO_SLOT = {
    105: "key_1",   # F13
    107: "key_2",   # F14
    113: "key_3",   # F15
    106: "key_4",   # F16
    64: "key_5",    # F17
    79: "key_6",    # F18
    80: "key_7",    # F19
    90: "key_8",    # F20
    # encoder_cw / encoder_ccw / encoder_click: no Mac equivalent (F21-F23).
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
