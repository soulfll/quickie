#pragma once
#include <Arduino.h>

// 8 direct-wired switches (no row/col matrix -- each key gets its own pin,
// wired switch-to-ground, read with the internal pull-up). That means a key
// reads HIGH by default and LOW when pressed.
#define NUM_KEYS 8
#define DEBOUNCE_MS 5

void keys_init();
void keys_scan();
