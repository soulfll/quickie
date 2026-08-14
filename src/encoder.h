#pragma once
#include <Arduino.h>

// Rotary encoder sits in the 9th grid slot: 2 pins for quadrature (A/B) plus
// its own push-button click.
void encoder_init();
void encoder_scan();
