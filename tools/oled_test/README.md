# OLED hardware test

For when the Quick-Key's screen shows garbage or nothing. It talks to the
screen directly (no libraries, none of the Quick-Key code) so it tests only the
wiring and the screen.

Flash it, watch the screen, and note which of the six patterns look right:

```bash
pio run -e oled_test_v4 -t upload     # new PCB
pio run -e oled_test -t upload        # original v3 PCB
```

To go back to the real firmware afterwards, flash it normally
(`pio run -e teensy40_v4 -t upload`).

It loops forever, 4 seconds per pattern, and prints which one is showing to the
serial monitor.

| # | Pattern | If it looks right, these work |
|---|---------|-------------------------------|
| 1 | Whole screen **white** | power, reset (RST), clock, data, chip select (CS), and DC when low (commands get through) |
| 2 | Whole screen **black** | DC when high (picture data gets through and is stored) |
| 3 | **Horizontal stripes** across the full width | the data path under load (many bytes in a row) |
| 4 | **Left half white**, right half black | column addressing and clock integrity |
| 5 | **One small box**, top-left corner | the same, at a fine scale |
| 6 | Stripes again, sent **4x slower** | marginal wires: see below |

## Reading the result

- **Pattern 1 stays black (or nothing ever changes):** the screen isn't hearing
  commands at all. Check VCC and GND first, then RST, CS, CLK (pin 19) and DATA
  (pin 18), and DC (pin 14 on the new board, 17 on the original).
- **1 is white but 2 shows noise or leftover pixels:** commands arrive but the
  picture data doesn't. That is almost always **DC** (it must go HIGH during data).
- **1 and 2 are right, but 3, 4 and 5 are scrambled or shifted:** data is arriving
  corrupted. Suspect **CLK** or **DATA** (a loose or marginal wire), or CS.
- **3 is messy but 6 (slow) is clean:** the wires are marginal at full speed.
  The fix is to slow the clock in `src/display.cpp` (`SPI_HALF_NS`), or shorten
  / re-solder the flying wires.
- **Everything is clean:** the wiring and screen are fine; the problem is in the
  firmware's startup or state.
