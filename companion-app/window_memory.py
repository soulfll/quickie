"""
Window memory (Windows only): remembers how each app's window was left, and
puts it back.

Two problems this solves for apps opened with a Quick-Key key:

  1. The app is already running (say the user minimized it with the "-"
     button) and the key is pressed again. Launching it a second time opens a
     new window at the app's default size. Instead, the existing window is
     brought back, which Windows restores to exactly where it was.

  2. The app was closed, and the user had sized it by hand (windowed but as
     large as the screen allows, not maximized). Many apps forget that and
     reopen at their default size. Here, every few seconds the size,
     position and maximized-or-not state of each app's window are noted in
     window_layouts.json, and applied again the next time the app is opened.

An app is matched to its windows by its program file (e.g. excel.exe), found
from what the key opens: "excel", a path to a .exe, or a Start Menu shortcut.
Store apps and anything that isn't a plain program are left alone. On other
operating systems, and on any error, everything here quietly does nothing and
the app just launches the normal way.

All the Windows calls live in _Native, so the logic can be tested against a
fake (see test_window_memory.py).
"""

import json
import os
import re
import sys
import threading
import time
from dataclasses import dataclass

from debuglog import debug

SAMPLE_SECONDS = 2.0        # how often window positions are noted
SETTLE_SECONDS = 3.0        # a new window is left alone this long before it is noted
FIND_TIMEOUT = 25.0         # how long to wait for a launched app's window to appear
TOLERANCE = 6               # pixels of difference that still counts as "in place"


@dataclass
class Win:
    hwnd: int
    exe: str            # e.g. "excel.exe"
    title: str
    rect: tuple         # (left, top, right, bottom) on screen
    iconic: bool        # minimized
    zoomed: bool        # maximized


# --------------------------------------------------------------------------
# The Windows calls
# --------------------------------------------------------------------------
class _Native:
    GW_OWNER = 4
    GWL_STYLE, GWL_EXSTYLE = -16, -20
    WS_CAPTION, WS_EX_TOOLWINDOW = 0xC00000, 0x80
    SW_SHOWNORMAL, SW_SHOWMAXIMIZED, SW_RESTORE = 1, 3, 9
    SWP_NOZORDER, SWP_NOACTIVATE, SWP_NOOWNERZORDER = 0x4, 0x10, 0x200
    DWMWA_CLOAKED = 14

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        self.ct, self.wt = ctypes, wintypes
        u = self.u = ctypes.WinDLL("user32", use_last_error=True)
        k = self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.dwm = ctypes.WinDLL("dwmapi", use_last_error=True)
        H, B, I, U, L = wintypes.HWND, wintypes.BOOL, ctypes.c_int, wintypes.UINT, wintypes.LPARAM

        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                        ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
        self.RECT = RECT

        def sig(fn, restype, *argtypes):
            fn.restype, fn.argtypes = restype, list(argtypes)

        self.EnumProc = ctypes.WINFUNCTYPE(B, H, L)
        sig(u.EnumWindows, B, self.EnumProc, L)
        sig(u.IsWindowVisible, B, H)
        sig(u.IsIconic, B, H)
        sig(u.IsZoomed, B, H)
        sig(u.GetWindow, H, H, U)
        sig(u.GetWindowLongW, wintypes.LONG, H, I)
        sig(u.GetWindowTextLengthW, I, H)
        sig(u.GetWindowTextW, I, H, wintypes.LPWSTR, I)
        sig(u.GetWindowRect, B, H, ctypes.POINTER(RECT))
        sig(u.GetWindowThreadProcessId, wintypes.DWORD, H, ctypes.POINTER(wintypes.DWORD))
        sig(u.ShowWindow, B, H, I)
        sig(u.SetWindowPos, B, H, H, I, I, I, I, U)
        sig(u.SetForegroundWindow, B, H)
        sig(u.SwitchToThisWindow, None, H, B)
        sig(u.MonitorFromRect, wintypes.HANDLE, ctypes.POINTER(RECT), wintypes.DWORD)
        sig(k.OpenProcess, wintypes.HANDLE, wintypes.DWORD, B, wintypes.DWORD)
        sig(k.QueryFullProcessImageNameW, B, wintypes.HANDLE, wintypes.DWORD,
            wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD))
        sig(k.CloseHandle, B, wintypes.HANDLE)
        sig(self.dwm.DwmGetWindowAttribute, ctypes.c_long, H, wintypes.DWORD,
            ctypes.c_void_p, wintypes.DWORD)

    def set_thread_dpi(self):
        """Report real pixels (not scaled ones) to this thread, so a saved
        position means the same thing when it is applied later."""
        try:
            self.u.SetThreadDpiAwarenessContext.argtypes = [self.ct.c_void_p]
            self.u.SetThreadDpiAwarenessContext(self.ct.c_void_p(-4))   # per-monitor v2
        except Exception:
            pass

    def _rect(self, hwnd):
        r = self.RECT()
        self.u.GetWindowRect(hwnd, self.ct.byref(r))
        return (r.left, r.top, r.right, r.bottom)

    def _exe_of(self, hwnd, cache):
        pid = self.wt.DWORD(0)
        self.u.GetWindowThreadProcessId(hwnd, self.ct.byref(pid))
        if pid.value in cache:
            return cache[pid.value]
        exe = ""
        handle = self.k.OpenProcess(0x1000, False, pid.value)     # query-limited-information
        if handle:
            try:
                size = self.wt.DWORD(1024)
                buf = self.ct.create_unicode_buffer(1024)
                if self.k.QueryFullProcessImageNameW(handle, 0, buf, self.ct.byref(size)):
                    exe = os.path.basename(buf.value).lower()
            finally:
                self.k.CloseHandle(handle)
        cache[pid.value] = exe
        return exe

    def list_windows(self):
        """Ordinary application windows, topmost first."""
        found, cache, u = [], {}, self.u

        def visit(hwnd, _lparam):
            try:
                if not u.IsWindowVisible(hwnd) or u.GetWindow(hwnd, self.GW_OWNER):
                    return True
                style = u.GetWindowLongW(hwnd, self.GWL_STYLE) & 0xFFFFFFFF
                exstyle = u.GetWindowLongW(hwnd, self.GWL_EXSTYLE) & 0xFFFFFFFF
                if exstyle & self.WS_EX_TOOLWINDOW or (style & self.WS_CAPTION) != self.WS_CAPTION:
                    return True                      # tool windows, splash screens, pop-ups
                cloaked = self.wt.DWORD(0)
                if self.dwm.DwmGetWindowAttribute(hwnd, self.DWMWA_CLOAKED, self.ct.byref(cloaked), 4) == 0 and cloaked.value:
                    return True                      # hidden "ghost" windows of suspended Store apps
                length = u.GetWindowTextLengthW(hwnd)
                if length == 0:
                    return True
                buf = self.ct.create_unicode_buffer(length + 1)
                u.GetWindowTextW(hwnd, buf, length + 1)
                iconic, zoomed = bool(u.IsIconic(hwnd)), bool(u.IsZoomed(hwnd))
                rect = self._rect(hwnd)
                if not iconic and (rect[2] - rect[0] < 200 or rect[3] - rect[1] < 120):
                    return True
                exe = self._exe_of(hwnd, cache)
                if exe:
                    found.append(Win(int(hwnd), exe, buf.value, rect, iconic, zoomed))
            except Exception:
                pass
            return True

        u.EnumWindows(self.EnumProc(visit), 0)
        return found

    def restore(self, hwnd):
        self.u.ShowWindow(hwnd, self.SW_RESTORE)        # back to exactly how it was before minimizing

    def show_normal(self, hwnd):
        self.u.ShowWindow(hwnd, self.SW_SHOWNORMAL)

    def show_maximized(self, hwnd):
        self.u.ShowWindow(hwnd, self.SW_SHOWMAXIMIZED)

    def set_rect(self, hwnd, rect):
        left, top, right, bottom = rect
        self.u.SetWindowPos(hwnd, None, left, top, right - left, bottom - top,
                            self.SWP_NOZORDER | self.SWP_NOACTIVATE | self.SWP_NOOWNERZORDER)

    def foreground(self, hwnd):
        self.u.SwitchToThisWindow(hwnd, True)
        self.u.SetForegroundWindow(hwnd)

    def rect_on_screen(self, rect):
        """False if the saved spot is on a monitor that isn't connected now."""
        r = self.RECT(*rect)
        return bool(self.u.MonitorFromRect(self.ct.byref(r), 0))       # 0 = no monitor: not on screen


_native_instance = None


def _native():
    global _native_instance
    if _native_instance is None:
        _native_instance = _Native()
    return _native_instance


def _now():
    return time.monotonic()


def _sleep(seconds):
    time.sleep(seconds)


# --------------------------------------------------------------------------
# Which program does a key open?
# --------------------------------------------------------------------------
_lnk_cache = {}


def _shortcut_target(path):
    """The program a Start Menu shortcut (.lnk) runs, or None."""
    if path in _lnk_cache:
        return _lnk_cache[path]
    target = None
    try:
        import comtypes
        import comtypes.client
        comtypes.CoInitialize()
        try:
            target = comtypes.client.CreateObject("WScript.Shell").CreateShortcut(path).TargetPath or None
        finally:
            comtypes.CoUninitialize()
    except Exception as e:
        debug(f"window memory: couldn't read shortcut {path}: {e}")
    _lnk_cache[path] = target
    return target


def expected_exe(value):
    """The program file name a key's "open an app" action will run, lower-case
    (e.g. "excel.exe"), or None if it can't be told or isn't a plain program."""
    text = os.path.expandvars(str(value or "").strip().strip('"'))
    if not text:
        return None
    if re.match(r"^[A-Za-z][A-Za-z0-9+.\-]+:(?![\\/])", text):
        return None                                   # a link like ms-teams:, not a program
    if text.lower().endswith(".lnk"):
        target = _shortcut_target(text)
        if not target:
            return None
        text = target
    name = re.split(r"[\\/]", text)[-1].lower()            # the file name, whichever kind of slash
    if not name:
        return None
    if not os.path.splitext(name)[1]:
        name += ".exe"                                # "excel" -> excel.exe
    if not name.endswith(".exe") or name in ("explorer.exe", "applicationframehost.exe"):
        return None                                   # documents, and Store apps hosted by Windows
    return name


def exes_for_config(config):
    """Every program the saved keys can open, for the background noting."""
    exes = set()
    for slots in config.get("profiles", {}).values():
        for actions in slots.values():
            for action in actions:
                if action.get("type", "app") == "app":
                    exe = expected_exe(action.get("value"))
                    if exe:
                        exes.add(exe)
    return exes


# --------------------------------------------------------------------------
# What was remembered
# --------------------------------------------------------------------------
_lock = threading.Lock()
_layouts = None            # exe -> {"state": "normal" | "maximized", "rect": [l, t, r, b] or None}
_placing = {}              # exe -> when its window was last being put back


def _layout_path():
    import config as config_store
    return os.path.join(config_store.data_dir(), "window_layouts.json")


def _load():
    global _layouts
    if _layouts is None:
        try:
            with open(_layout_path()) as f:
                _layouts = json.load(f)
            if not isinstance(_layouts, dict):
                _layouts = {}
        except (OSError, ValueError):
            _layouts = {}
    return _layouts


def _save():
    path = _layout_path()
    try:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(_layouts, f, indent=2)
        os.replace(tmp, path)
    except OSError as e:
        debug(f"window memory: couldn't save layouts: {e}")


# --------------------------------------------------------------------------
# Bringing a window back, and putting it where it was
# --------------------------------------------------------------------------
def bring_back_if_open(value):
    """If this app already has a window, bring it back (un-minimizing it to
    where it was) and return True, so the caller doesn't launch it again."""
    if sys.platform != "win32" and _native_instance is None:
        return False
    exe = expected_exe(value)
    if not exe:
        return False
    native = _native()
    windows = [w for w in native.list_windows() if w.exe == exe]
    if not windows:
        return False
    top = windows[0]
    if top.iconic:
        native.restore(top.hwnd)
    native.foreground(top.hwnd)
    return True


def _matches(win, layout):
    if layout.get("state") == "maximized":
        return win.zoomed
    rect = layout.get("rect")
    if not rect:
        return True
    return (not win.zoomed and not win.iconic
            and all(abs(a - b) <= TOLERANCE for a, b in zip(win.rect, rect)))


def _apply(native, hwnd, layout):
    rect = layout.get("rect")
    if rect and native.rect_on_screen(rect):
        native.show_normal(hwnd)            # leave maximized/minimized first, so the size takes
        native.set_rect(hwnd, rect)
    if layout.get("state") == "maximized":
        native.show_maximized(hwnd)


def _place_worker(exe, layout):
    native = _native()
    native.set_thread_dpi()
    _placing[exe] = _now()
    try:
        deadline = _now() + FIND_TIMEOUT
        hwnd = None
        while hwnd is None and _now() < deadline:
            for w in native.list_windows():
                if w.exe == exe:
                    hwnd = w.hwnd
                    break
            if hwnd is None:
                _sleep(0.25)
        if hwnd is None:
            return
        # Apps often move their own window a moment after showing it, so check
        # and re-apply a few times.
        for _ in range(4):
            _apply(native, hwnd, layout)
            _sleep(0.7)
            current = next((w for w in native.list_windows() if w.hwnd == hwnd), None)
            if current is None or _matches(current, layout):
                break
    except Exception as e:
        debug(f"window memory: placing {exe} failed: {e}")
    finally:
        _sleep(1.0)
        _placing.pop(exe, None)


def place_when_ready(value):
    """Call right after launching an app: puts its window where it was left
    last time, once the window appears. Returns immediately."""
    if sys.platform != "win32" and _native_instance is None:
        return
    exe = expected_exe(value)
    if not exe:
        return
    with _lock:
        layout = _load().get(exe)
    _placing[exe] = _now()       # hold off noting this app until it has been put back
    if not layout:
        threading.Timer(SETTLE_SECONDS + 1, lambda: _placing.pop(exe, None)).start()
        return                   # nothing remembered yet; the next launch will have it
    threading.Thread(target=_place_worker, args=(exe, dict(layout)), daemon=True).start()


# --------------------------------------------------------------------------
# Noting how windows are left
# --------------------------------------------------------------------------
def _sample_once(native, exes, first_seen):
    """One pass: note the topmost window of each watched app. Returns True if
    anything changed."""
    now = _now()
    seen, noted, dirty = set(), set(), False
    with _lock:
        layouts = _load()
        for w in native.list_windows():
            seen.add(w.hwnd)
            if w.exe not in exes or w.exe in noted:
                continue
            first = first_seen.setdefault(w.hwnd, now)
            if w.exe in _placing or now - first < SETTLE_SECONDS or w.iconic:
                continue          # being put back, brand new, or minimized: leave what we had
            noted.add(w.exe)
            if w.zoomed:
                entry = {"state": "maximized", "rect": (layouts.get(w.exe) or {}).get("rect")}
            else:
                entry = {"state": "normal", "rect": list(w.rect)}
            if layouts.get(w.exe) != entry:
                layouts[w.exe] = entry
                dirty = True
    for hwnd in [h for h in first_seen if h not in seen]:
        del first_seen[hwnd]
    if dirty:
        _save()
    return dirty


def _sampler(get_exes):
    native = _native()
    native.set_thread_dpi()
    first_seen = {}
    while True:
        _sleep(SAMPLE_SECONDS)
        try:
            exes = get_exes()
            if exes:
                _sample_once(native, exes, first_seen)
        except Exception as e:
            debug(f"window memory: sampling failed: {e}")


def start_tracking(get_exes):
    """Start noting window positions in the background. get_exes() returns the
    set of program names to watch (see exes_for_config)."""
    if sys.platform != "win32":
        return
    threading.Thread(target=_sampler, args=(get_exes,), daemon=True).start()
