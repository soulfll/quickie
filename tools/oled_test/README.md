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

## Wire-order finder

If the pattern test shows commands working (pattern 1 lights up) but pictures
never appear, and you suspect two of the three flying wires (CS, DC, RST) are
swapped, flash the finder instead:

```bash
pio run -e oled_pins_v4 -t upload
```

It tries all six ways the three wires could be connected. The Teensy's own LED
blinks 1-6 times to say which way is next, then the screen shows white and then
stripes. The way whose stripes are clean and even is the correct one.

## What this has found before

- **DC wire not reaching the screen** (new board, Oct 2026): pattern 1 was white
  but 2-5 never showed, and the finder gave clean stripes for no order other
  than the real wiring. A multimeter reading of the screen's DC pin during
  patterns 2-6 (should be about 3.3 V) tells you for certain. Re-seating the wire
  fixed it.
- Always unplug USB before touching wires. A spark from a wire brushing the
  wrong pin on a live board is how most accidental shorts happen.
