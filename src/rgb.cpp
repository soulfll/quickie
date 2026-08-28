#include "rgb.h"

// STUBBED OUT -- do not wire anything up against this file yet.
//
// This was originally written for a single addressable WS2812 LED on pin 11.
// The real PCB (hardware/new project v.3 new layout.kicad_pcb) turned out to
// be different in two ways:
//   1. Pin 11 is actually the rotary encoder's click button (see
//      encoder.cpp) -- claiming it here would fight the encoder for the pin.
//   2. There's no WS2812 on the board at all. Instead there are 3 separate
//      plain LEDs (D1/D2/D3), each with its cathode grounded, but none of
//      their anodes are routed to a Teensy pin yet in this layout.
//
// Once we know which Teensy pins D1/D2/D3's anodes are meant to land on,
// this needs to become 3 independent PWM outputs (analogWrite per pin), not
// FastLED/WS2812 -- completely different approach, so rewriting rather than
// patching the pin number once that's decided.

void rgb_init() {
  // no-op until real LED pins are known
}

void rgb_set(uint8_t r, uint8_t g, uint8_t b) {
  (void)r;
  (void)g;
  (void)b;
  // no-op until real LED pins are known
}

void rgb_update() {
  // no-op until real LED pins are known
}
