#pragma once
#include <Arduino.h>

// 2.08" 256x64 SPI OLED (SH1122) driven through U8g2 -- pins and wiring
// notes are in display.cpp.

void display_init();
void display_show_text(const char *line1, const char *line2 = nullptr);
void display_update();
