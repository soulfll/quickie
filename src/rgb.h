#pragma once
#include <Arduino.h>

// One addressable RGB LED (WS2812-style) standing in for what would've been
// separate single-color LEDs per function (mic/webcam/volume/etc). Whatever
// state we want to show (recording, muted, idle...) just becomes a color set
// from elsewhere in the firmware or a command from the companion app.

void rgb_init();
void rgb_set(uint8_t r, uint8_t g, uint8_t b);
void rgb_update();
