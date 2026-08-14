#include "rgb.h"
#include <FastLED.h>

// TODO: change once wired -- data pin and LED count.
#define RGB_PIN 11
#define RGB_COUNT 1

static CRGB leds[RGB_COUNT];

void rgb_init() {
  FastLED.addLeds<WS2812, RGB_PIN, GRB>(leds, RGB_COUNT);
  FastLED.setBrightness(64);
  rgb_set(0, 0, 0);
}

void rgb_set(uint8_t r, uint8_t g, uint8_t b) {
  for (int i = 0; i < RGB_COUNT; i++) {
    leds[i] = CRGB(r, g, b);
  }
}

void rgb_update() {
  FastLED.show();
}
