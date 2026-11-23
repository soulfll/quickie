# Building the Quick-Key installer on Windows

This turns the companion app into a single `QuickKeySetup.exe` that anyone can
double-click: Next, accept the privacy notice, Finish. The person using it needs
no Python, no Git and no terminal.

It has to be built **on Windows** (PyInstaller can't make a Windows `.exe` on a
Mac). You do this once per release, not once per user.

## One-time setup on the Windows PC

1. **Python 3.10 or newer** from <https://www.python.org/downloads/>.
   On the first screen tick **"Add python.exe to PATH"**.
2. **Git** from <https://git-scm.com/download/win> (defaults are fine), only to
   fetch the code. Skip it if you copy the folder over some other way.
3. **Inno Setup 6** from <https://jrsoftware.org/isdl.php> (defaults are fine).
   This is what makes the installer. Without it you still get the app itself.

Open a **new** terminal afterwards so it picks up the PATH change.

## Build

```
git clone https://github.com/soulfll/quickie.git
cd quickie\companion-app
build_windows.bat
```

(Already cloned? Run `git pull` instead of the clone, then `cd quickie\companion-app`.)

`build_windows.bat` does everything: it makes a private Python environment,
installs the app's libraries, builds the app, then builds the installer. The
first run takes a few minutes. When it says DONE you have:

| File | What it is |
|------|-----------|
| `dist\QuickKey.exe` | The app on its own. Double-click it to try it. |
| `installer\Output\QuickKeySetup.exe` | The installer. This is what you hand to people. |

If it says BUILD FAILED, scroll up to the first red/error line and send that.

## Test it before sharing it

1. **Try `dist\QuickKey.exe` first.** Plug in the Quick-Key and open it.
   - A window opens, and the Quick-Key's screen changes from "Waiting for the
     app" to the profile name.
2. **Assign a key**: *Assign via Key Press...*, press a key, add a website
   (e.g. `https://example.com`), press the key again to confirm. Press it once
   more: the site should open and the screen should show what it did.
3. **Turn the dial**: system volume changes and the volume bar shows on the screen.
4. **Close the app and open it again**: the assignment is still there.
5. **Run `QuickKeySetup.exe`** (ideally on a PC that has never had Python on it).
   Install, tick the launch option, and repeat step 2.
6. **Uninstall** from Windows Settings > Apps and check it goes away.

Your assignments are stored in `%APPDATA%\Quick-Key\config.json`, so they survive
restarts, upgrades and reinstalls. If the app ever closes unexpectedly, it writes
what went wrong to `%APPDATA%\Quick-Key\error.log` (paste the end of that file).

## Windows warnings you will see (all normal for an unsigned app)

- **"Windows protected your PC" (SmartScreen)** when running the installer:
  click **More info**, then **Run anyway**. It goes away only with a paid
  code-signing certificate, which isn't needed at this stage.
- **Antivirus flags the `.exe`**: apps made with PyInstaller are sometimes
  flagged by mistake. Add an exception, or submit the file as a false positive
  to the antivirus vendor.
- **Windows 11 "Smart App Control" blocks it outright** (no "Run anyway"
  button): that setting only allows signed apps. It's a security setting, so
  turning it off is a decision for the PC's owner (Windows Security > App &
  browser control > Smart App Control).
- **No driver is needed** for the Quick-Key itself: Windows has built-in
  keyboard and serial drivers for it.

## Releasing it

1. On GitHub: **Releases > Draft a new release**, pick a tag such as `v1.0.0`,
   and attach `QuickKeySetup.exe`.
2. Turn on the landing page: **Settings > Pages > Deploy from a branch**, branch
   `main`, folder `/docs`. Its download button points at the latest release.

## If the built app misbehaves

- **Closes immediately / error dialog:** read `%APPDATA%\Quick-Key\error.log`.
- **`ModuleNotFoundError` in that log:** add the missing package's name to the
  `for pkg in (...)` list near the top of `quickkey.spec` and rebuild.
- **Keys press but nothing launches:** check the status line at the bottom of the
  app window. It names the key it saw (F13 to F20). If it never changes, another
  program is grabbing those keys.
- **Screen never leaves "Waiting for the app":** another copy of Quick-Key (or a
  serial monitor) is holding the port. Close it and replug the Quick-Key.

## Rebuilding after code changes

`git pull`, then run `build_windows.bat` again. Bump `MyAppVersion` in
`installer\quickkey_installer.iss` first so Windows treats it as an upgrade.
