"""
Finds the apps installed on this computer, so the picker can show a plain
searchable list of names instead of a file dialog.

A file dialog is the wrong tool for this: on macOS an .app is secretly a
folder, so dialogs treat it as one (you can open it but not pick it), and on
Windows the real programs are buried under Program Files. Both OSes already
keep a tidy list of launchable apps, so we read that instead:

  - macOS:   the *.app bundles in the Applications folders
  - Windows: the shortcuts (.lnk) in the Start Menu -- the same list the
             Start Menu itself shows. os.startfile() can launch a .lnk
             directly, same as double-clicking it.

Each result is (display name, path to launch).
"""

import os
import sys


def _mac_apps():
    roots = [
        "/Applications",
        "/System/Applications",
        os.path.expanduser("~/Applications"),
    ]
    found = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, _files in os.walk(root):
            depth = dirpath[len(root):].count(os.sep)
            apps = [d for d in dirnames if d.endswith(".app")]
            for d in apps:
                found.setdefault(d[:-4], os.path.join(dirpath, d))
            # Never descend into an .app, and only look one folder deep
            # (e.g. /Applications/Utilities, vendor folders).
            dirnames[:] = [d for d in dirnames if not d.endswith(".app")] if depth < 1 else []
    return found


def _windows_apps():
    roots = [
        os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                     "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("APPDATA", ""),
                     "Microsoft", "Windows", "Start Menu", "Programs"),
    ]
    found = {}
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for name in files:
                stem, ext = os.path.splitext(name)
                if ext.lower() != ".lnk" or "uninstall" in stem.lower():
                    continue
                found.setdefault(stem, os.path.join(dirpath, name))
    return found


def find_installed_apps():
    """Returns [(name, path), ...] sorted by name, case-insensitive."""
    if sys.platform == "darwin":
        found = _mac_apps()
    elif sys.platform == "win32":
        found = _windows_apps()
    else:
        found = {}
    return sorted(found.items(), key=lambda item: item[0].lower())


def filter_apps(apps, text):
    """Case-insensitive 'contains' filter for the search box."""
    needle = text.strip().lower()
    if not needle:
        return list(apps)
    return [(name, path) for name, path in apps if needle in name.lower()]
