// OLED wire-order finder. If the screen shows garbage but power and the clock/data
// wires are fine, the usual cause is two of the three flying wires (CS, DC, RST)
// being swapped -- the screen lists them as RST, DC, CS but the Teensy pins run
// 14, 15, 16 in a different order, so it is easy to mix them up.
//
// Rather than guess, this tries all SIX ways the three wires could be connected.
// For each one the Teensy's own LED blinks N times (N = 1..6) to say which way it is
// about to try, then the screen shows all-white for 2 seconds, then clean
// horizontal STRIPES for 4 seconds. The way that gives clean, evenly spaced
// stripes is the right one; tell me its number (the LED blink count).
#include <Arduino.h>
#include "../../src/display_pins.h"

// The three wires, by the Teensy pin they are physically soldered to.
// (These are the same three pins as in display_pins.h; only the ROLE each one
// plays is tried in every order.)
#ifdef BOARD_V4
static const uint8_t PIN_A = 14, PIN_B = 15, PIN_C = 16;
#else
static const uint8_t PIN_A = 17, PIN_B = 20, PIN_C = 16;
#endif

// Each row: which pin plays {CS, DC, RST}.
struct Way { uint8_t cs, dc, rst; };
static const Way WAYS[6] = {
  {PIN_C, PIN_A, PIN_B},   // 1: current setting in display_pins.h  (CS=C, DC=A, RST=B)
  {PIN_A, PIN_C, PIN_B},   // 2: CS and DC swapped
  {PIN_C, PIN_B, PIN_A},   // 3: DC and RST swapped
  {PIN_B, PIN_A, PIN_C},   // 4: CS and RST swapped
  {PIN_A, PIN_B, PIN_C},   // 5
  {PIN_B, PIN_C, PIN_A},   // 6
};

static uint8_t pCS, pDC, pRST;

static void byte_out(uint8_t b) {
  for (int i = 7; i >= 0; i--) {
    digitalWriteFast(OLED_DATA, (b >> i) & 1);
    delayNanoseconds(125);
    digitalWriteFast(OLED_CLK, HIGH);
    delayNanoseconds(125);
    digitalWriteFast(OLED_CLK, LOW);
  }
}
static void cmd(uint8_t c)              { digitalWrite(pCS, LOW); digitalWrite(pDC, LOW); byte_out(c); digitalWrite(pCS, HIGH); }
static void cmd2(uint8_t c, uint8_t a)  { digitalWrite(pCS, LOW); digitalWrite(pDC, LOW); byte_out(c); byte_out(a); digitalWrite(pCS, HIGH); }

static void init_display() {
  digitalWrite(pRST, LOW);  delay(20);
  digitalWrite(pRST, HIGH); delay(50);
  cmd(0xAE); cmd(0x40); cmd(0xA0); cmd(0xC0);
  cmd2(0x81, 0x80); cmd2(0xA8, 0x3F); cmd2(0xAD, 0x81); cmd2(0xD5, 0x50);
  cmd2(0xD3, 0x00); cmd2(0xD9, 0x22); cmd2(0xDB, 0x35); cmd2(0xDC, 0x35);
  cmd(0x30);
  delay(5);
  cmd(0xAF);
  delay(100);
}

static void stripes() {
  for (int y = 0; y < 64; y++) {
    cmd2(0xB0, (uint8_t)y); cmd(0x00); cmd(0x10);
    digitalWrite(pCS, LOW); digitalWrite(pDC, HIGH);
    for (int i = 0; i < 128; i++) byte_out((y & 1) ? 0x00 : 0xFF);
    digitalWrite(pCS, HIGH);
  }
}

static void blink(int n) {
  for (int i = 0; i < n; i++) { digitalWrite(LED_BUILTIN, HIGH); delay(250); digitalWrite(LED_BUILTIN, LOW); delay(250); }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  pinMode(OLED_CLK, OUTPUT);
  pinMode(OLED_DATA, OUTPUT);
  pinMode(PIN_A, OUTPUT); pinMode(PIN_B, OUTPUT); pinMode(PIN_C, OUTPUT);
  digitalWrite(OLED_CLK, LOW);
  delay(300);
}

void loop() {
  for (int k = 0; k < 6; k++) {
    pCS = WAYS[k].cs; pDC = WAYS[k].dc; pRST = WAYS[k].rst;
    digitalWrite(pCS, HIGH); digitalWrite(pRST, HIGH);
    Serial.printf("way %d: CS=pin %d  DC=pin %d  RST=pin %d\n", k + 1, pCS, pDC, pRST);
    blink(k + 1);                 // LED blinks k+1 times = "this is way number k+1"
    delay(800);
    init_display();
    cmd(0xA5);                    // everything on -> white
    delay(2000);
    cmd(0xA4);                    // show the picture memory again
    stripes();                    // clean evenly spaced stripes = THIS is the right way
    delay(4000);
  }
}
