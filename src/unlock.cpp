#include "unlock.h"
#include <EEPROM.h>

// EEPROM layout: [0] marker, [1] length, [2...] the characters.
static const int ADDR_MARKER = 0;
static const int ADDR_LEN = 1;
static const int ADDR_DATA = 2;
static const uint8_t MARKER = 0xA7;   // says "a password was saved here"

// Timing for the sign-in screen. The first tap dismisses the lock screen's
// cover; the box then needs a moment to appear before it can take typing.
// If the first characters go missing on a slower laptop, raise BOX_WAIT_MS.
static const int WAKE_GAP_MS = 400;
static const int BOX_WAIT_MS = 800;
static const int CHAR_GAP_MS = 15;    // typing in one burst can drop characters
static const int ENTER_GAP_MS = 150;

static char stored[UNLOCK_MAX_LEN + 1];
static uint8_t stored_len = 0;

void unlock_init() {
  stored_len = 0;
  if (EEPROM.read(ADDR_MARKER) != MARKER) return;
  uint8_t n = EEPROM.read(ADDR_LEN);
  if (n == 0 || n > UNLOCK_MAX_LEN) return;
  for (uint8_t i = 0; i < n; i++) stored[i] = (char)EEPROM.read(ADDR_DATA + i);
  stored[n] = '\0';
  stored_len = n;
}

bool unlock_has_password() { return stored_len > 0; }

bool unlock_set(const char *password) {
  size_t n = strlen(password);
  if (n > UNLOCK_MAX_LEN) return false;
  for (size_t i = 0; i < n; i++) {
    if (password[i] < 32 || password[i] > 126) return false;   // plain ASCII only
  }
  if (n == 0) {
    EEPROM.update(ADDR_MARKER, 0);        // clear
    stored_len = 0;
    return true;
  }
  for (size_t i = 0; i < n; i++) EEPROM.update(ADDR_DATA + i, (uint8_t)password[i]);
  EEPROM.update(ADDR_LEN, (uint8_t)n);
  EEPROM.update(ADDR_MARKER, MARKER);     // last, so a half-finished save is ignored
  memcpy(stored, password, n);
  stored[n] = '\0';
  stored_len = (uint8_t)n;
  return true;
}

static void tap(uint16_t code) {
  Keyboard.press(code);
  delay(20);
  Keyboard.release(code);
}

void unlock_type() {
  if (stored_len == 0) return;
  // Shift types nothing on its own, so it is harmless if the sign-in box is
  // already showing -- but it is enough to dismiss the lock screen's cover.
  tap(KEY_LEFT_SHIFT);
  delay(WAKE_GAP_MS);
  tap(KEY_LEFT_SHIFT);
  delay(BOX_WAIT_MS);
  for (uint8_t i = 0; i < stored_len; i++) {
    Keyboard.write(stored[i]);
    delay(CHAR_GAP_MS);
  }
  delay(ENTER_GAP_MS);
  tap(KEY_ENTER);
}
