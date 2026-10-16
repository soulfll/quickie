#include "display.h"
#include <U8g2lib.h>

// 2.08" 256x64 OLED (GME25664-65, SH1122 controller), 7-pin SPI.
//
// Wiring on the PCB's J1OLED1 header (hardware/new project v.3 new layout.kicad_pcb):
//   VCC -> 3.3V, GND -> GND
//   SDA -> Teensy 18  (the module's SPI data line, NOT I2C)
//   SCL -> Teensy 19  (the module's SPI clock line, NOT I2C)
// RST / DC / CS aren't on that header, so they're jumper-wired straight to
// free Teensy pins -- change these three if you wire them elsewhere. Avoid
// 18/19 (those are the header's SDA/SCL, already on the module) and, on the
// v3 board, 12/13/15 (the PCB puts the LEDs D1/D2/D3 on them).
#define OLED_CLK 19
#define OLED_DATA 18
#ifdef BOARD_V4
// New PCB (`-e teensy40_v4`): 14/15/16 are all unconnected on that board.
#define OLED_DC 14
#define OLED_CS 16
#define OLED_RST 15
#else
// Original v3 PCB -- this is the wiring verified working on that board.
#define OLED_CS 16
#define OLED_DC 17
#define OLED_RST 20
#endif

// Software (bit-banged) SPI, same approach as the vendor STM32 demo. Hardware
// SPI on the Teensy would use pins 11/12/13, and 11 is the encoder click.
// Argument order is: rotation, clock, data, cs, dc, reset.
static U8G2_SH1122_256X64_F_4W_SW_SPI oled(
    U8G2_R0, OLED_CLK, OLED_DATA, OLED_CS, OLED_DC, OLED_RST);

void display_init() {
  // SPI is write-only here, so there's no way to detect a missing or
  // miswired screen from code -- it just stays blank.
  oled.begin();
  display_show_text("Quickie", "booting...");
}

void display_show_text(const char *line1, const char *line2) {
  oled.clearBuffer();
  oled.setFont(u8g2_font_helvB14_tf);
  oled.drawStr(0, 18, line1);
  if (line2) {
    oled.setFont(u8g2_font_helvR10_tf);
    oled.drawStr(0, 40, line2);
  }
  oled.sendBuffer();
}

void display_update() {
  // Placeholder for anything that needs to redraw every loop (e.g. an
  // animation or live status). Nothing yet -- display_show_text() handles
  // one-shot updates for now.
}
