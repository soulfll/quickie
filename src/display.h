#pragma once
#include <Arduino.h>

// 2.08" 256x64 SPI OLED (SH1122) driven through U8g2 -- pins and wiring
// notes are in display.cpp.
//
// Four things can be on screen:
//   - "Waiting for the app" until the companion app has said hello,
//   - the active profile's name (the normal, idle screen),
//   - a volume bar for a moment after the dial is turned,
//   - a message from the app: a title and up to three lines, used to show what
//     a key does when it's pressed and each step of assigning a key.
// The screen is only redrawn when something changes (plus a slow refresh), so
// it never holds up reading the keys and dial.

void display_init();
void display_update();                      // call every loop

// Which profile is active (the idle screen).
void display_set_profile(const char *name);

// Show a message. Any line may be null/empty. A non-sticky message goes away
// by itself after a few seconds; a sticky one stays until replaced or
// display_clear_message() (used for steps that wait for the user).
void display_show(const char *title, const char *line1, const char *line2,
                  const char *line3, bool sticky);
void display_clear_message();

// Volume overlay, like the one the OS shows: a bar of segments that fills as
// the volume goes up. percent is 0-100. Shown for ~2 seconds, on top of
// whatever else is on screen. The app reads the computer's real volume and
// sends it (the dial itself only says "up" or "down").
void display_show_volume(int percent, bool muted);
