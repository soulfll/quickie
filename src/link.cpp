#include "link.h"
#include "display.h"

static char line_buf[200];
static size_t line_len = 0;

// SPLIT-BEGIN (this block is compiled by a host-side test too -- keep it free
// of Arduino-only calls)
// Splits `text` on '|' IN PLACE (the separators become '\0') and points
// fields[0..n-1] at the pieces. Returns n, at most max_fields. A missing field
// is just left out; the caller treats those as empty.
static int split_fields(char *text, char **fields, int max_fields) {
  int n = 0;
  char *p = text;
  while (n < max_fields) {
    fields[n++] = p;
    char *bar = strchr(p, '|');
    if (!bar) break;
    *bar = '\0';
    p = bar + 1;
  }
  return n;
}
// SPLIT-END

static void show_message(char *args, bool sticky) {
  char *f[4];
  int n = split_fields(args, f, 4);
  display_show(n > 0 ? f[0] : "", n > 1 ? f[1] : "", n > 2 ? f[2] : "",
               n > 3 ? f[3] : "", sticky);
}

static void handle_line(char *line) {
  if (line[0] == 'P' && line[1] == ':') {
    display_set_profile(line + 2);
  } else if (line[0] == 'S' && line[1] == ':') {
    show_message(line + 2, false);
  } else if (line[0] == 'A' && line[1] == ':') {
    show_message(line + 2, true);
  } else if (line[0] == 'V' && line[1] == ':') {
    // V:<percent 0-100>|<muted 0 or 1>
    int percent = atoi(line + 2);
    const char *bar = strchr(line + 2, '|');
    display_show_volume(percent, bar && atoi(bar + 1) != 0);
  } else if (line[0] == 'C' && line[1] == '\0') {
    display_clear_message();
  }
  // Anything else (the "H" hello, or stray keystrokes typed into the serial
  // monitor) is ignored on purpose.
}

void link_poll() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (line_len > 0) {
        line_buf[line_len] = '\0';
        handle_line(line_buf);
      }
      line_len = 0;
    } else if (line_len < sizeof(line_buf) - 1) {
      line_buf[line_len++] = c;
    }
    // A line longer than the buffer just gets cut off at its end.
  }
}
