#include "encoder.h"

// TODO: replace with real wiring once the encoder is wired up.
static const uint8_t PIN_A = 8;
static const uint8_t PIN_B = 9;
static const uint8_t PIN_CLICK = 10;

// Same idea as the 8 keys: dedicated unused keycodes, one tap per detent/click.
// CW / CCW map to F21 / F22, the click maps to F23. What they *do* (volume,
// scroll, app-specific action, etc.) is decided in the companion app.
#define KEY_ENC_CW KEY_F21
#define KEY_ENC_CCW KEY_F22
#define KEY_ENC_CLICK KEY_F23
#define ENCODER_DEBOUNCE_MS 5

static uint8_t last_ab = 0;
static bool click_state = false;
static unsigned long last_click_change = 0;

void encoder_init() {
  pinMode(PIN_A, INPUT_PULLUP);
  pinMode(PIN_B, INPUT_PULLUP);
  pinMode(PIN_CLICK, INPUT_PULLUP);
  last_ab = (digitalRead(PIN_A) << 1) | digitalRead(PIN_B);
}

static void tap(uint16_t code) {
  Keyboard.press(code);
  Keyboard.release(code);
}

void encoder_scan() {
  // Simple 2-bit quadrature decode. Good enough for a mechanical detent
  // encoder; if we get missed/double steps once it's wired, swap this for a
  // full 4x state-table decode or the Encoder library.
  uint8_t a = digitalRead(PIN_A);
  uint8_t b = digitalRead(PIN_B);
  uint8_t ab = (a << 1) | b;

  if (ab != last_ab) {
    if (last_ab == 0b00 && ab == 0b01) {
      tap(KEY_ENC_CW);
      Serial.println("encoder CW");
    } else if (last_ab == 0b00 && ab == 0b10) {
      tap(KEY_ENC_CCW);
      Serial.println("encoder CCW");
    }
    last_ab = ab;
  }

  bool pressed = (digitalRead(PIN_CLICK) == LOW);
  unsigned long now = millis();
  if (pressed != click_state && (now - last_click_change) > ENCODER_DEBOUNCE_MS) {
    click_state = pressed;
    last_click_change = now;
    if (pressed) {
      Keyboard.press(KEY_ENC_CLICK);
      Serial.println("encoder click down");
    } else {
      Keyboard.release(KEY_ENC_CLICK);
      Serial.println("encoder click up");
    }
  }
}
