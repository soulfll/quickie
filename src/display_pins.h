#pragma once
// Which Teensy pins the 2.08" OLED is wired to. Shared by the real firmware
// (display.cpp) and the hardware test (tools/oled_test) so they can never
// disagree about the wiring.

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
