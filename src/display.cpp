#include "display.h"
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1     // Teensy resets it via software; no dedicated pin.
#define OLED_I2C_ADDR 0x3C // TODO: 0x3D on some boards -- check yours if blank.

static Adafruit_SSD1306 oled(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);
static bool oled_ok = false;

void display_init() {
  Wire.begin();
  oled_ok = oled.begin(SSD1306_SWITCHCAPVCC, OLED_I2C_ADDR);
  if (!oled_ok) {
    Serial.println("SSD1306 not found -- check wiring/I2C address");
    return;
  }
  oled.clearDisplay();
  oled.setTextColor(SSD1306_WHITE);
  display_show_text("Quickie", "booting...");
}

void display_show_text(const char *line1, const char *line2) {
  if (!oled_ok) return;

  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.println(line1);
  if (line2) {
    oled.setCursor(0, 12);
    oled.println(line2);
  }
  oled.display();
}

void display_update() {
  // Placeholder for anything that needs to redraw every loop (e.g. an
  // animation or live status). Nothing yet -- display_show_text() handles
  // one-shot updates for now.
}
