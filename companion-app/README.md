# Quickie companion app

The Windows-side app: lets you assign any number of installed apps to each
physical key/encoder action on the Quickie pad, listens for the Teensy's
keypresses, and launches whatever's assigned.

## How it fits together

The Teensy firmware doesn't know or care what each key "does" -- it just
reports "physical key N went down" as a USB HID keyboard, using F13-F23 (keys
otherwise unused by anything, so no shortcut collisions). This app listens
globally for exactly those keycodes and does the rest: looking up which
app(s) are assigned to that key and launching them. All the "any key can open
any number of apps" flexibility lives here, in `config.json` -- nothing about
it is hardcoded in firmware.

## Setup

```bash
cd companion-app
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

On **macOS**, Tkinter (the GUI toolkit) isn't bundled with Homebrew's Python
by default -- if you get `ModuleNotFoundError: No module named '_tkinter'`,
run `brew install python-tk@3.14` (or whatever your Python version is) first.

## Running

```bash
python3 main.py
```

This opens the GUI (one row per key + encoder action) and starts the global
key listener in the background.

There are two ways to assign apps to a slot:

- **Mouse**: "Add App..." on any row, browse to the app, done. Works without
  the Teensy plugged in -- good for setting things up before hardware exists.
- **Assign via Key Press...** (the "verification system" from the design
  flowchart): click it, press the *physical* key you want to assign (no more
  guessing which key is "Key 3"), pick the app(s) in the file picker -- they
  show up in amber as unconfirmed -- then press that **same key again** to
  confirm and save. Press a *different* key instead and it cancels with
  nothing saved. Needs the Teensy plugged in and flashed, since it listens
  for a real keypress.

Either way, changes save to `config.json` immediately.

## Profiles

The dropdown at the top switches between named profiles -- each one is a
complete, independent 8-key + encoder mapping (e.g. a "streaming" profile vs
a "gaming" profile). "New Profile..." creates an empty one. Right now
switching is GUI-only; there's no hardware trigger to change the active
profile from the device itself yet -- worth deciding once the encoder
behavior is nailed down (long-press to cycle profiles? auto-switch based on
which app is focused on Windows?).

## Testing without the Teensy plugged in

You don't need the hardware to test the GUI or config save/load -- just run
the app and add/remove apps from slots.

To test the *listener* (global key detection), the Teensy needs to actually
be plugged in and flashed, since there's no F13-F24 on a normal keyboard to
press. Once it's wired:

- **macOS**: grant your terminal app Accessibility permission (System
  Settings -> Privacy & Security -> Accessibility) or `pynput` can't see
  global keystrokes -- it'll just hang. The Teensy shows up as a normal USB
  HID keyboard to any OS, so you can plug it into the Mac and test the full
  listener -> slot lookup -> launch pipeline here; on Mac, `launcher.py`
  falls back to `open` so you'll still see *something* launch per key.
- **Windows**: no extra permission needed; `os.startfile()` is the real,
  final launch path.

## Files

- `main.py` -- entry point, wires everything together
- `listener.py` -- global keyboard listener (pynput), maps VK codes to slot names
- `keymap.py` -- VK code <-> slot name mapping (must match firmware's key order)
- `config.py` -- load/save `config.json` (slot -> list of app paths)
- `launcher.py` -- the one OS-specific piece; actually opens an app
- `gui.py` -- Tkinter UI for assigning apps to slots
- `config.example.json` -- template; real `config.json` is gitignored since it holds your local app paths
