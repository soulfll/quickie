#include "display.h"
#include <U8g2lib.h>

#include "display_pins.h"   // OLED wiring: which Teensy pin goes to which screen pin

// Software (bit-banged) SPI, same approach as the vendor STM32 demo. Hardware
// SPI on the Teensy would use pins 11/12/13, and 11 is the encoder click.
// Argument order is: rotation, clock, data, cs, dc, reset.
static U8G2_SH1122_256X64_F_4W_SW_SPI oled(
    U8G2_R0, OLED_CLK, OLED_DATA, OLED_CS, OLED_DC, OLED_RST);

// ---------------------------------------------------------------------------
// Frame sending.
//
// The whole screen is drawn into U8g2's buffer and then sent in one go by
// flush_frame() below -- NOT with U8g2's sendBuffer() or its partial
// updateDisplayArea(). For this screen U8g2 stores 8 pixels per byte side by
// side and its SH1122 driver reads those bytes straight through, so it only
// works when each send spans the full 256-pixel width (a partial update
// scrambles the picture -- found the hard way). Its software SPI is also
// slow; flush_frame() does the same transfer with direct pin writes at the
// timing the SH1122 figure in U8g2 uses (250 ns per bit).
// ---------------------------------------------------------------------------

static const uint32_t SPI_HALF_NS = 125;   // 250 ns per bit

static void spi_byte(uint8_t b) {
  for (int i = 7; i >= 0; i--) {           // MSB first, clock idles low, sampled on the rising edge
    digitalWriteFast(OLED_DATA, (b >> i) & 1);
    delayNanoseconds(SPI_HALF_NS);
    digitalWriteFast(OLED_CLK, HIGH);
    delayNanoseconds(SPI_HALF_NS);
    digitalWriteFast(OLED_CLK, LOW);
  }
}

// U8g2's buffer for this screen is 64 rows of 32 bytes; each byte holds 8
// pixels, leftmost in bit 7. The SH1122 wants 4 bits per pixel, two pixels per
// byte, so every source byte becomes four output bytes (lit pixel = 0xF).
static void flush_frame() {
  const uint8_t *buf = oled.getBufferPtr();
  for (int y = 0; y < 64; y++) {
    digitalWriteFast(OLED_CS, LOW);
    delayNanoseconds(40);
    digitalWriteFast(OLED_DC, LOW);        // command: row address, then column 0
    spi_byte(0xB0);
    spi_byte((uint8_t)y);
    spi_byte(0x00);
    spi_byte(0x10);
    digitalWriteFast(OLED_DC, HIGH);       // data
    const uint8_t *row = buf + y * 32;
    for (int k = 0; k < 32; k++) {
      uint8_t b = row[k];
      for (int shift = 6; shift >= 0; shift -= 2) {
        uint8_t pair = (b >> shift) & 3;   // bit 1 = left pixel, bit 0 = right pixel
        spi_byte(((pair & 2) ? 0xF0 : 0x00) | ((pair & 1) ? 0x0F : 0x00));
      }
    }
    delayNanoseconds(40);
    digitalWriteFast(OLED_CS, HIGH);
  }
}

// ---------------------------------------------------------------------------
// What is shown.
// ---------------------------------------------------------------------------

static const int NAME_LEN = 24;
static const int LINE_LEN = 48;
static const int SCREEN_W = 256;
static const int MARGIN = 8;
static const int TEXT_W = SCREEN_W - 2 * MARGIN;                 // pixels available for text
static const unsigned long MESSAGE_MS = 4000;                    // how long a non-sticky message stays
static const unsigned long VOLUME_MS = 2000;                     // how long the volume bar stays
static const int VOL_SEGMENTS = 18;                              // segments in the volume bar
static const unsigned long REFRESH_MS = 1000;
static const unsigned long STARTUP_WAIT_MS = 250;

static char active[NAME_LEN] = "";

static bool message_on = false;
static bool message_sticky = false;
static unsigned long message_until = 0;
static char msg_title[LINE_LEN] = "";
static char msg_lines[3][LINE_LEN];

static bool volume_on = false;
static unsigned long volume_until = 0;
static int volume_percent = 0;
static bool volume_muted = false;

static bool dirty = true;
static unsigned long init_ms = 0;
static unsigned long last_flush_ms = 0;

// Copies src into dst, replacing anything that isn't plain printable ASCII
// with '?' (the fonts only cover that safely).
static void copy_clean(char *dst, const char *src, size_t cap) {
  size_t n = 0;
  if (src) {
    for (; src[n] && n < cap - 1; n++) {
      char c = src[n];
      dst[n] = (c >= 32 && c < 127) ? c : '?';
    }
  }
  dst[n] = '\0';
}

// Draws `text` at (MARGIN, baseline) in the current font, shortening it with a
// trailing '~' if it would run off the screen.
static void draw_fitted(int baseline, const char *text) {
  char buf[LINE_LEN];
  copy_clean(buf, text, sizeof(buf));
  size_t len = strlen(buf);
  if (oled.getStrWidth(buf) > TEXT_W) {
    while (len > 1 && oled.getStrWidth(buf) > TEXT_W) {
      buf[--len] = '\0';
      buf[len - 1] = '~';
    }
  }
  oled.drawStr(MARGIN, baseline, buf);
}

void display_set_profile(const char *name) {
  copy_clean(active, name, NAME_LEN);
  dirty = true;
}

void display_show(const char *title, const char *line1, const char *line2,
                  const char *line3, bool sticky) {
  copy_clean(msg_title, title, sizeof(msg_title));
  copy_clean(msg_lines[0], line1, sizeof(msg_lines[0]));
  copy_clean(msg_lines[1], line2, sizeof(msg_lines[1]));
  copy_clean(msg_lines[2], line3, sizeof(msg_lines[2]));
  message_on = true;
  message_sticky = sticky;
  message_until = millis() + MESSAGE_MS;
  dirty = true;
}

void display_clear_message() {
  message_on = false;
  dirty = true;
}

void display_show_volume(int percent, bool muted) {
  if (percent < 0) percent = 0;
  if (percent > 100) percent = 100;
  volume_percent = percent;
  volume_muted = muted;
  volume_on = true;
  volume_until = millis() + VOLUME_MS;
  dirty = true;
}

static void draw_waiting() {
  oled.setFont(u8g2_font_helvB14_tf);
  draw_fitted(28, "Quick-Key");
  oled.setFont(u8g2_font_helvR10_tf);
  draw_fitted(50, "Waiting for the app...");
}

static void draw_profile() {
  oled.setFont(u8g2_font_helvR10_tf);
  draw_fitted(18, "Profile");
  // Biggest font the name fits in.
  oled.setFont(u8g2_font_helvB18_tf);
  if (oled.getStrWidth(active) > TEXT_W) oled.setFont(u8g2_font_helvB14_tf);
  draw_fitted(52, active);
}

static void draw_message() {
  oled.setFont(u8g2_font_helvB14_tf);
  draw_fitted(16, msg_title);
  oled.setFont(u8g2_font_helvR10_tf);
  for (int i = 0; i < 3; i++) {
    draw_fitted(33 + i * 14, msg_lines[i]);
  }
}

// "Volume" (or "Muted") and the percentage on top, then a rectangle holding
// VOL_SEGMENTS segments that fill in from the left as the volume rises.
static void draw_volume() {
  oled.setFont(u8g2_font_helvB14_tf);
  draw_fitted(18, volume_muted ? "Muted" : "Volume");

  char pct[8];
  snprintf(pct, sizeof(pct), "%d%%", volume_muted ? 0 : volume_percent);
  oled.drawStr(SCREEN_W - MARGIN - oled.getStrWidth(pct), 18, pct);

  const int FRAME_X = 6, FRAME_Y = 26, FRAME_W = 244, FRAME_H = 34;
  const int SEG_W = 11, SEG_GAP = 2, SEG_H = 22;
  const int pitch = SEG_W + SEG_GAP;
  const int inner_w = VOL_SEGMENTS * pitch - SEG_GAP;
  const int x0 = FRAME_X + (FRAME_W - inner_w) / 2;
  const int y0 = FRAME_Y + (FRAME_H - SEG_H) / 2;

  oled.drawRFrame(FRAME_X, FRAME_Y, FRAME_W, FRAME_H, 3);

  int lit = volume_muted ? 0 : (volume_percent * VOL_SEGMENTS + 50) / 100;
  if (!volume_muted && volume_percent > 0 && lit == 0) lit = 1;   // quiet but not silent: show something
  for (int i = 0; i < lit; i++) {
    oled.drawBox(x0 + i * pitch, y0, SEG_W, SEG_H);
  }
}

void display_init() {
  // SPI is write-only here, so there's no way to detect a missing or
  // miswired screen from code -- it just stays blank.
  oled.begin();
  init_ms = millis();
  dirty = true;
}

void display_update() {
  unsigned long now = millis();
  if (now - init_ms < STARTUP_WAIT_MS) return;          // let the screen finish waking up

  if (volume_on && (long)(now - volume_until) >= 0) {
    volume_on = false;                                   // volume bar is over
    dirty = true;
  }
  if (message_on && !message_sticky && (long)(now - message_until) >= 0) {
    message_on = false;                                  // timed message is over
    dirty = true;
  }

  // Even when nothing has changed the screen is re-sent about once a second.
  // That is cheap (about 20 ms), and it means a screen that was still waking
  // up when the first frame went out, or that glitched, fixes itself instead
  // of staying blank until the next change.
  bool changed = dirty;
  if (!changed && now - last_flush_ms < REFRESH_MS) return;
  dirty = false;
  last_flush_ms = now;

  oled.clearBuffer();
  oled.setDrawColor(1);
  if (volume_on) {
    draw_volume();
  } else if (message_on) {
    draw_message();
  } else if (active[0] != '\0') {
    draw_profile();
  } else {
    draw_waiting();
  }

  uint32_t t0 = micros();
  flush_frame();
  if (changed) {   // only log real changes, not the once-a-second refresh
    Serial.printf("display redraw took %lu us\n", (unsigned long)(micros() - t0));
  }
}
