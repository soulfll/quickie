#include "rgb.h"

// STUBBED OUT -- do not wire anything up against this file yet.
//
// This was originally written for a single addressable WS2812 LED on pin 11.
// The real PCB (hardware/new project v.3 new layout.kicad_pcb) turned out to
// be different in two ways:
//   1. Pin 11 is actually the rotary encoder's click button (see
//      encoder.cpp) -- claiming it here would fight the encoder for the pin.
//   2. There's no WS2812 on the board at all. Instead there are 3 separate
//      plain LEDs, each with a series resistor and its cathode grounded:
//        D1 <- R1 <- Teensy pin 12
//        D2 <- R2 <- Teensy pin 13
//        D3 <- R3 <- Teensy pin 15
//      (An earlier version of this comment said they weren't routed -- that
//      was wrong; it missed the resistors between the pins and the LEDs.)
//
// This needs to become 3 independent outputs (digitalWrite or analogWrite
// per pin), not FastLED/WS2812 -- completely different approach, so
// rewriting rather than patching the pin number.

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
