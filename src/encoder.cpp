#include "encoder.h"

// Real wiring, pulled directly from hardware/new project v.3 new layout.kicad_pcb
static const uint8_t PIN_A = 9;
static const uint8_t PIN_B = 10;
static const uint8_t PIN_CLICK = 11;

// The dial is a volume knob: turn = volume up / down, click = mute. These are
// the standard media keys, so they work on any computer straight away with no
// software installed (unlike the 8 keys, whose meaning lives in the app).
#define KEY_ENC_CW KEY_MEDIA_VOLUME_INC
#define KEY_ENC_CCW KEY_MEDIA_VOLUME_DEC
#define KEY_ENC_CLICK KEY_MEDIA_MUTE
#define ENCODER_DEBOUNCE_MS 5

static bool click_state = false;
static unsigned long last_click_change = 0;

// Rotation is decoded in an interrupt, not by polling in loop(). Redrawing
// the screen takes a few milliseconds, and a fast spin of the dial would
// otherwise slip through while the loop was busy. The ISR only counts steps;
// encoder_scan() turns the counts into key taps.
//
// Counting is done the standard robust way: every edge on A or B moves the
// dial one quarter-step forward or back (a Gray-code sequence), and a click of
// the dial is reported only once EDGES_PER_DETENT of them have added up in
// the same direction. Contact bounce goes forward and straight back, so it
// cancels to nothing instead of counting as extra steps.
//
// EDGES_PER_DETENT is how many A/B edges one click of the dial produces: 4 for
// the common EC11 dial. If one click gives TWO volume steps, your dial makes 8
// edges per click -- set it to 8. If it takes TWO clicks to give one step, your
// dial makes 2 per click -- set it to 2.
#define EDGES_PER_DETENT 4

static volatile uint8_t isr_last_ab = 0;
static volatile int8_t isr_acc = 0;
static volatile uint8_t pending_cw = 0;
static volatile uint8_t pending_ccw = 0;

// DECODE-BEGIN (compiled by a host-side test too -- keep it free of Arduino calls)
// Indexed by (previous A/B << 2) | new A/B, with A in the high bit.
//   clockwise:         00 -> 01 -> 11 -> 10 -> 00   (+1 each)
//   counter-clockwise: 00 -> 10 -> 11 -> 01 -> 00   (-1 each)
// Everything else (no change, or an impossible two-pin jump) counts as 0.
static const int8_t QUAD_DELTA[16] = {
     0, +1, -1,  0,
    -1,  0,  0, +1,
    +1,  0,  0, -1,
     0, -1, +1,  0,
};

static void quad_step(uint8_t ab) {
  int8_t d = QUAD_DELTA[(isr_last_ab << 2) | ab];
  isr_last_ab = ab;
  if (d == 0) return;
  isr_acc += d;
  if (isr_acc >= EDGES_PER_DETENT) {
    isr_acc = 0;
    pending_cw++;
  } else if (isr_acc <= -EDGES_PER_DETENT) {
    isr_acc = 0;
    pending_ccw++;
  }
}
// DECODE-END

static void encoder_isr() {
  quad_step((digitalRead(PIN_A) << 1) | digitalRead(PIN_B));
}

void encoder_init() {
  pinMode(PIN_A, INPUT_PULLUP);
  pinMode(PIN_B, INPUT_PULLUP);
  pinMode(PIN_CLICK, INPUT_PULLUP);
  isr_last_ab = (digitalRead(PIN_A) << 1) | digitalRead(PIN_B);
  attachInterrupt(digitalPinToInterrupt(PIN_A), encoder_isr, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_B), encoder_isr, CHANGE);
}

static void tap(uint16_t code) {
  Keyboard.press(code);
  Keyboard.release(code);
}

void encoder_scan() {
  noInterrupts();
  uint8_t cw = pending_cw;
  uint8_t ccw = pending_ccw;
  pending_cw = 0;
  pending_ccw = 0;
  interrupts();

  for (uint8_t i = 0; i < cw; i++) {
    tap(KEY_ENC_CW);
    Serial.println("encoder CW");
  }
  for (uint8_t i = 0; i < ccw; i++) {
    tap(KEY_ENC_CCW);
    Serial.println("encoder CCW");
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
