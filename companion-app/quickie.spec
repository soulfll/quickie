# PyInstaller spec for Quickie. Bundles main.py and every local module
# (gui.py, config.py, launcher.py, listener.py, keymap.py, action_picker.py)
# plus a full Python interpreter into one .exe -- the end user never
# installs Python or pip installs anything.
#
# Run on WINDOWS (PyInstaller can't cross-compile a Windows .exe from Mac):
#   pip install pyinstaller
#   pyinstaller quickie.spec
#
# Output lands in dist/Quickie.exe -- see BUILD_WINDOWS.md for the full
# walkthrough including wrapping this in a real installer.

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # pynput loads its Windows backend dynamically based on sys.platform,
    # which PyInstaller's static import scanner can miss. Spelling it out
    # here avoids a "No module named pynput.keyboard._win32" crash at
    # runtime on a machine that doesn't have a dev Python install to fall
    # back on.
    hiddenimports=['pynput.keyboard._win32', 'pynput.mouse._win32'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Quickie',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # no terminal window -- just the GUI, like a real app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # add a .ico file here later and uncomment for a real app icon
)
