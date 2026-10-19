#pragma once
#include <Arduino.h>

// Listens for short text commands from the companion app over the USB serial
// connection, one per line. Fields inside a command are separated by '|'.
//
//   P:<profile name>                       the active profile (idle screen)
//   S:<title>|<line1>|<line2>|<line3>      show a message for a few seconds
//   A:<title>|<line1>|<line2>|<line3>      show a message that stays until the
//                                          next one (a step that waits for you)
//   C                                      clear any message (back to idle)
//   V:<percent 0-100>|<muted 0/1>          show the volume bar for a moment
//   H                                      "hello" -- app connected (ignored)
//
// Call link_poll() every loop; it never blocks.
void link_poll();
