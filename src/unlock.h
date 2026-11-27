#pragma once
#include <Arduino.h>

// An "unlock" key: the Quick-Key types a stored password ITSELF, as a real USB
// keyboard. That is the only way to type at the Windows sign-in screen --
// Windows keeps that screen on a protected desktop that no program on the PC
// (including the companion app) can see keys on or type into, but it accepts
// keystrokes from keyboard hardware.
//
// The password is set from the companion app (over the USB serial link) and
// kept in the Teensy's EEPROM, so it survives unplugging. It is stored as
// PLAIN TEXT on the device: anyone holding the Quick-Key could read it out.
// Fine for a demo; don't use it for a password that matters.
//
// While a password is stored, the unlock key types it instead of sending its
// normal F-key. With none stored, the key behaves like any other.

#define UNLOCK_KEY_INDEX 6        // Key 7 (0-based index 6)
#define UNLOCK_MAX_LEN 63

void unlock_init();                      // call once in setup()
bool unlock_has_password();
// Stores `password` (printable ASCII, up to UNLOCK_MAX_LEN characters). An
// empty string clears it. Returns false (and changes nothing) if it is too long
// or has a character that can't be typed.
bool unlock_set(const char *password);
// Wakes the lock screen, types the password and presses Enter. Blocks for
// about two seconds.
void unlock_type();
