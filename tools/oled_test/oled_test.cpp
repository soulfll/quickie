// OLED hardware test. Flash it on its own (see platformio.ini, env oled_test_v4
// / oled_test) when the screen shows garbage, to find out which wire or stage
// is at fault. It uses no libraries and none of the Quick-Key code: just the
// pins in src/display_pins.h and the screen's own startup commands.
//
// It loops through these patterns, 4 seconds each, and prints which one is up:
//   1  ALL ON       whole screen white   needs: power, RST, CLK, DATA, CS, DC(low)
//   2  ALL OFF      whole screen black   needs the above plus DC(high): data writes
//   3  STRIPES      horizontal white and black lines across the whole screen
//   4  LEFT HALF    left half white, right half black
//   5  CORNER BOX   one small white box in the top-left corner
//   6  STRIPES, SLOW  the same stripes sent 4x slower (a clean 6 but a messy 3
//                     means the wires are marginal at full speed)
// What each failure means is written up in tools/oled_test/README.md.
#include <Arduino.h>
#include "../../src/display_pins.h"

static uint32_t half_ns = 125;            // 250 ns per bit, the screen's rated speed

static void byte_out(uint8_t b) {
  for (int i = 7; i >= 0; i--) {
    digitalWriteFast(OLED_DATA, (b >> i) & 1);
    delayNanoseconds(half_ns);
    digitalWriteFast(OLED_CLK, HIGH);
    delayNanoseconds(half_ns);
    digitalWriteFast(OLED_CLK, LOW);
  }
}

static void cmd(uint8_t c) {
  digitalWriteFast(OLED_CS, LOW);
  digitalWriteFast(OLED_DC, LOW);
  byte_out(c);
  digitalWriteFast(OLED_CS, HIGH);
}

static void cmd2(uint8_t c, uint8_t a) {
  digitalWriteFast(OLED_CS, LOW);
  digitalWriteFast(OLED_DC, LOW);
  byte_out(c);
  byte_out(a);
  digitalWriteFast(OLED_CS, HIGH);
}

// Hardware reset, then the same startup commands the real firmware's screen
// library sends (U8g2's SH1122 256x64 sequence), then display on.
static void init_display() {
  digitalWrite(OLED_RST, LOW);
  delay(20);
  digitalWrite(OLED_RST, HIGH);
  delay(50);
  cmd(0xAE);               // display off
  cmd(0x40);               // start line
  cmd(0xA0);               // remap
  cmd(0xC0);               // remap
  cmd2(0x81, 0x80);        // contrast
  cmd2(0xA8, 0x3F);        // 1/64 duty
  cmd2(0xAD, 0x81);        // built-in DC-DC
  cmd2(0xD5, 0x50);        // clock divide / oscillator
  cmd2(0xD3, 0x00);        // display offset
  cmd2(0xD9, 0x22);        // pre/discharge period
  cmd2(0xDB, 0x35);        // VCOM level
  cmd2(0xDC, 0x35);        // pre-charge voltage
  cmd(0x30);               // discharge level
  delay(5);
  cmd(0xAF);               // display on
  delay(100);
}

// Sends one pixel row: 128 data bytes (256 pixels, 4 bits each).
// value_for(i) gives the byte for column-byte i (0..127).
template <typename F>
static void send_row(int y, F value_for) {
  cmd2(0xB0, (uint8_t)y);
  cmd(0x00);
  cmd(0x10);
  digitalWriteFast(OLED_CS, LOW);
  digitalWriteFast(OLED_DC, HIGH);
  for (int i = 0; i < 128; i++) byte_out(value_for(i));
  digitalWriteFast(OLED_CS, HIGH);
}

template <typename F>
static void fill(F row_value) {            // row_value(y, i) -> byte
  for (int y = 0; y < 64; y++) send_row(y, [&](int i) { return row_value(y, i); });
}

static void stage(int n, const char *name) {
  Serial.printf("stage %d: %s\n", n, name);
}

void setup() {
  Serial.begin(115200);
  pinMode(OLED_CLK, OUTPUT);
  pinMode(OLED_DATA, OUTPUT);
  pinMode(OLED_CS, OUTPUT);
  pinMode(OLED_DC, OUTPUT);
  pinMode(OLED_RST, OUTPUT);
  digitalWrite(OLED_CS, HIGH);
  digitalWrite(OLED_CLK, LOW);
  digitalWrite(OLED_RST, HIGH);
  delay(300);
}

void loop() {
  half_ns = 125;
  init_display();

  stage(1, "ALL ON (whole screen should be white)");
  cmd(0xA5);
  delay(4000);

  stage(2, "ALL OFF (whole screen should be black)");
  cmd(0xA4);                                              // back to showing the screen memory
  fill([](int, int) { return (uint8_t)0x00; });
  delay(4000);

  stage(3, "STRIPES (horizontal white/black lines)");
  fill([](int y, int) { return (uint8_t)((y & 1) ? 0x00 : 0xFF); });
  delay(4000);

  stage(4, "LEFT HALF (left half white, right half black)");
  fill([](int, int i) { return (uint8_t)(i < 64 ? 0xFF : 0x00); });
  delay(4000);

  stage(5, "CORNER BOX (one small white box, top-left)");
  fill([](int y, int i) { return (uint8_t)((y < 16 && i < 16) ? 0xFF : 0x00); });
  delay(4000);

  stage(6, "STRIPES, SLOW CLOCK (same as 3, sent 4x slower)");
  half_ns = 500;
  fill([](int y, int) { return (uint8_t)((y & 1) ? 0x00 : 0xFF); });
  delay(4000);
}
