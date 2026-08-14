#pragma once
#include <Arduino.h>

// Small I2C OLED (assuming SSD1306 128x64 -- change SCREEN_WIDTH/HEIGHT and
// the Adafruit_SSD1306 constructor args in display.cpp if yours differs).

void display_init();
void display_show_text(const char *line1, const char *line2 = nullptr);
void display_update();
