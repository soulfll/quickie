#include <Arduino.h>
#include "keys.h"
#include "encoder.h"
#include "rgb.h"
#include "display.h"

void setup() {
  Serial.begin(115200);

  keys_init();
  encoder_init();
  rgb_init();
  display_init();
}

void loop() {
  keys_scan();
  encoder_scan();
  rgb_update();
  display_update();
}
