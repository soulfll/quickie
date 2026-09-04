# Building a real Windows installer for Quickie

This turns the companion app from "clone a repo, make a venv, pip install"
into a single `QuickieSetup.exe` that anyone can download and double-click --
Next, accept the privacy notice, Finish, done. No Python, no Git, no
terminal required on the end user's machine.

This has to be built **on Windows** -- PyInstaller can't produce a Windows
`.exe` from a Mac. Run everything below on the Windows laptop.

## 1. Build the app itself with PyInstaller

From `companion-app`, with your existing virtual environment:

```
.venv\Scripts\python -m pip install pyinstaller
.venv\Scripts\pyinstaller quickie.spec
```

This produces `dist\Quickie.exe` -- a single file with Python and every
dependency bundled in. You can actually double-click that file right now to
confirm it runs standalone before moving on to the installer wrapper.

If it fails to launch with something like
`ModuleNotFoundError: No module named 'pynput.keyboard._win32'`, that means
PyInstaller's import scanner missed a dynamically-loaded piece -- add the
missing module name to the `hiddenimports` list near the top of
`quickie.spec` and rebuild.

## 2. Install Inno Setup (free, one-time)

Download and install from <https://jrsoftware.org/isdl.php> -- defaults are
fine, just click through.

## 3. Build the installer

Open `installer\quickie_installer.iss` in the Inno Setup Compiler (it
should be in your Start Menu after installing) and click **Build > Compile**
(or press F9).

That produces `installer\Output\QuickieSetup.exe` -- this is the real
deliverable. Running it gives a normal Windows installer experience:
welcome screen, a privacy notice the user has to accept to continue,
optional desktop shortcut, optional "launch at Windows startup," and a
proper uninstaller registered with Windows.

## 4. Ship it

`QuickieSetup.exe` is a single file -- share it however you'd share any
installer (a GitHub Release attachment, a direct download link, USB drive,
whatever). The person running it never needs to know this was a Python
project at all.

## Rebuilding after code changes

Whenever `main.py` or any of the other `.py` files change, redo steps 1 and
3 (no need to reinstall Inno Setup again) to produce an updated
`QuickieSetup.exe`.

## A note on Windows SmartScreen

The very first time someone runs `QuickieSetup.exe`, Windows may show a
blue "Windows protected your PC" SmartScreen warning -- this happens to
*any* new, unsigned installer, not just this one. Clicking "More info" then
"Run anyway" gets past it. This warning goes away once the file has enough
of a reputation with Microsoft, or permanently if the `.exe` gets digitally
code-signed (a paid certificate, not something to worry about at this
stage).
