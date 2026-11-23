# PyInstaller spec for Quick-Key. Bundles main.py and every local module
# (gui.py, config.py, launcher.py, listener.py, keymap.py, action_picker.py)
# plus a full Python interpreter into one .exe -- the end user never
# installs Python or pip installs anything.
#
# Run on WINDOWS (PyInstaller can't cross-compile a Windows .exe from Mac):
#   pip install pyinstaller
#   pyinstaller quickkey.spec
#
# Output lands in dist/QuickKey.exe -- see BUILD_WINDOWS.md for the full
# walkthrough including wrapping this in a real installer.

# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

# The libraries below pick their platform backend at runtime (pynput's Windows
# keyboard hook, pyserial's Windows port lister, pycaw/comtypes for the volume
# bar), which PyInstaller's static scan can miss -- the app then crashes on a
# PC with no Python installed. Including every submodule of each is the
# reliable fix, and costs only a little size.
hidden = []
for pkg in ('pynput', 'serial', 'pycaw', 'comtypes'):
    hidden += collect_submodules(pkg)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
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
    name='QuickKey',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,   # off: UPX-packed exes are flagged by antivirus far more often
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
