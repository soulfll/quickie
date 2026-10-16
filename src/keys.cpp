#include "keys.h"

#ifdef BOARD_V4
// New PCB (teensytesttrey schematic), built with `-e teensy40_v4`:
// the 8 switches SW2..SW9 sit on pins 0-7 in a straight run. Which physical
// grid slot each index lands in isn't known from the schematic alone -- press
// each key and watch the serial monitor to map "key N" to a position.
// Verified on the board: reading left-to-right, top-to-bottom the grid is
//   0 1 [encoder] / 2 3 4 / 5 6 7, so key N here is already "Key N+1" in the app.
static const uint8_t key_pins[NUM_KEYS] = {0, 1, 2, 3, 4, 5, 6, 7};
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
        Keyboard.press(key_codes[i]);
        Serial.printf("key %d down (code %d)\n", i, key_codes[i]);
      } else {
        Keyboard.release(key_codes[i]);
        Serial.printf("key %d up\n", i);
      }
    }
  }
}
