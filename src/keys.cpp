#include "keys.h"
#include "unlock.h"

#ifdef BOARD_V4
// New PCB (teensytesttrey schematic), built with `-e teensy40_v4`:
// the 8 switches SW2..SW9 sit on pins 0-7. We want "Key N" in the app to read
// left-to-right, top-to-bottom:
//   Key1 Key2 [dial]
//   Key3 Key4 Key5
//   Key6 Key7 Key8
// On the board, each row came out mirrored with the pins in numeric order
// (it read 2 1 / 5 4 3 / 8 7 6), so the list below is that order flipped
// within each row. The pin at each physical position, in reading order:
//   pins 1 0 [dial] / 4 3 2 / 7 6 5   (key_pins[i] is the pin for Key i+1)
static const uint8_t key_pins[NUM_KEYS] = {1, 0, 4, 3, 2, 7, 6, 5};
#else
// Original v3 PCB, pulled directly from hardware/new project v.3 new layout.kicad_pcb
// (grid reads left-to-right, top-to-bottom; bottom-left slot is the encoder,
// not a key, which is why pin 6 / a "K7" switch don't appear here):
//   K1=0 K2=1 K3=2 (row 1) | K4=3 K5=4 K6=5 (row 2) | K8=7 K9=8 (row 3)
static const uint8_t key_pins[NUM_KEYS] = {0, 1, 2, 3, 4, 5, 7, 8};
#endif

// Each key sends its own dedicated, otherwise-unused keycode. Nothing else on
// a normal keyboard uses F13-F20, so these can't collide with real shortcuts,
// and the Windows companion app listens for exactly these codes to decide
// which app(s) to launch. What each key "means" lives entirely in that app,
// not here -- firmware's only job is "this physical key went down/up".
static const uint16_t key_codes[NUM_KEYS] = {
    KEY_F13, KEY_F14, KEY_F15, KEY_F16,
    KEY_F17, KEY_F18, KEY_F19, KEY_F20,
};

static bool key_state[NUM_KEYS] = {false};
// True while a key press was handled by the unlock key (typed a password), so
// the matching release must not send an F-key release that never had a press.
static bool key_swallowed[NUM_KEYS] = {false};
static unsigned long last_change[NUM_KEYS] = {0};

void keys_init() {
  for (int i = 0; i < NUM_KEYS; i++) {
    pinMode(key_pins[i], INPUT_PULLUP);
  }
}

void keys_scan() {
  unsigned long now = millis();

  for (int i = 0; i < NUM_KEYS; i++) {
    bool pressed = (digitalRead(key_pins[i]) == LOW);

    if (pressed != key_state[i] && (now - last_change[i]) > DEBOUNCE_MS) {
      key_state[i] = pressed;
      last_change[i] = now;

      if (pressed) {
        if (i == UNLOCK_KEY_INDEX && unlock_has_password()) {
          // The unlock key: type the stored password ourselves (works at the
          // Windows sign-in screen, where the app can't). Never printed.
          key_swallowed[i] = true;
          Serial.printf("key %d down (typing the stored password)\n", i);
          unlock_type();
        } else {
          Keyboard.press(key_codes[i]);
          Serial.printf("key %d down (code %d)\n", i, key_codes[i]);
        }
      } else {
        if (key_swallowed[i]) {
          key_swallowed[i] = false;
        } else {
          Keyboard.release(key_codes[i]);
        }
        Serial.printf("key %d up\n", i);
      }
    }
  }
}
