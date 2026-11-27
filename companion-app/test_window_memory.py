"""Tests for window_memory.py against a fake window system (no Windows needed).
Run:  python test_window_memory.py"""
import os
import sys
import tempfile

import window_memory as wm
from window_memory import Win


class FakeNative:
    """A few pretend windows. Calls are recorded so tests can check what happened."""

    def __init__(self):
        self.windows = []                 # topmost first
        self.log = []
        self.screen = (0, 0, 1920, 1080)
        self.app_moves_window_to = None   # simulate an app that resizes itself right after opening

    def set_thread_dpi(self): pass

    def list_windows(self):
        return list(self.windows)

    def _get(self, hwnd):
        return next(w for w in self.windows if w.hwnd == hwnd)

    def restore(self, hwnd):
        w = self._get(hwnd); w.iconic = False; self.log.append(("restore", hwnd))

    def show_normal(self, hwnd):
        w = self._get(hwnd); w.iconic = w.zoomed = False; self.log.append(("normal", hwnd))

    def show_maximized(self, hwnd):
        w = self._get(hwnd); w.zoomed = True; self.log.append(("maximize", hwnd))

    def set_rect(self, hwnd, rect):
        w = self._get(hwnd)
        w.rect = self.app_moves_window_to or tuple(rect)
        self.app_moves_window_to = None   # the app only fights the first attempt
        self.log.append(("rect", hwnd, tuple(rect)))

    def foreground(self, hwnd): self.log.append(("foreground", hwnd))

    def rect_on_screen(self, rect):
        l, t, r, b = self.screen
        return rect[0] < r and rect[2] > l and rect[1] < b and rect[3] > t


def fresh(tmpdir):
    fake = FakeNative()
    wm._native_instance = fake
    wm._layouts = None
    wm._placing.clear()
    wm._layout_path = lambda: os.path.join(tmpdir, "window_layouts.json")
    clock = {"t": 0.0}
    wm._now = lambda: clock["t"]
    wm._sleep = lambda s: clock.__setitem__("t", clock["t"] + s)
    return fake, clock


def test_expected_exe():
    cases = {
        "excel": "excel.exe",
        "winword": "winword.exe",
        r"C:\Program Files\Microsoft Office\root\Office16\EXCEL.EXE": "excel.exe",
        "C:/Windows/System32/notepad.exe": "notepad.exe",
        '"C:\\Apps\\My App.exe"': "my app.exe",
        "ms-teams:": None,
        "https://example.com": None,
        r"C:\Windows\explorer.exe": None,
        r"C:\docs\report.pdf": None,
        "": None,
        None: None,
    }
    for value, want in cases.items():
        assert wm.expected_exe(value) == want, (value, wm.expected_exe(value), want)
    print("expected_exe: ok")


def test_bring_back(tmp):
    fake, _ = fresh(tmp)
    fake.windows = [Win(1, "chrome.exe", "x", (0, 0, 900, 700), False, False),
                    Win(2, "excel.exe", "Book1", (100, 50, 1500, 950), True, False)]   # minimized
    assert wm.bring_back_if_open("excel") is True
    assert ("restore", 2) in fake.log and ("foreground", 2) in fake.log and not fake.windows[1].iconic
    fake.log.clear()
    assert wm.bring_back_if_open("outlook") is False            # not open: caller should launch it
    assert fake.log == []
    fake.windows = [Win(3, "excel.exe", "Book1", (0, 0, 1920, 1080), False, True)]      # already showing
    assert wm.bring_back_if_open("excel") is True
    assert ("restore", 3) not in fake.log and ("foreground", 3) in fake.log
    print("bring_back_if_open: ok")


def test_remembers_and_restores(tmp):
    fake, clock = fresh(tmp)
    big_windowed = (20, 10, 1900, 1040)          # "windowed, as large as it can be", NOT maximized
    fake.windows = [Win(7, "excel.exe", "Book1", big_windowed, False, False)]
    first_seen = {}
    wm._sample_once(fake, {"excel.exe"}, first_seen)
    assert wm._load() == {}, "a brand-new window must not be noted yet"
    clock["t"] += 4
    assert wm._sample_once(fake, {"excel.exe"}, first_seen) is True
    assert wm._load()["excel.exe"] == {"state": "normal", "rect": list(big_windowed)}

    # minimized windows must not overwrite what is known
    fake.windows[0].iconic, fake.windows[0].rect = True, (-32000, -32000, -31840, -31972)
    assert wm._sample_once(fake, {"excel.exe"}, first_seen) is False
    assert wm._load()["excel.exe"]["rect"] == list(big_windowed)

    # maximized: state recorded, the windowed size is kept for restore-down
    fake.windows[0].iconic, fake.windows[0].zoomed, fake.windows[0].rect = False, True, (-8, -8, 1928, 1088)
    wm._sample_once(fake, {"excel.exe"}, first_seen)
    assert wm._load()["excel.exe"] == {"state": "maximized", "rect": list(big_windowed)}

    # saved to disk, and read back in a "new session"
    assert os.path.exists(os.path.join(tmp, "window_layouts.json"))
    wm._layouts = None
    assert wm._load()["excel.exe"]["state"] == "maximized"

    # the app is closed, reopened at its default size, and put back
    wm._layouts["excel.exe"] = {"state": "normal", "rect": list(big_windowed)}
    fake.windows = [Win(8, "excel.exe", "Book1", (300, 200, 1100, 800), False, False)]
    fake.log.clear()
    wm.place_when_ready("excel")
    import time as _t
    deadline = _t.time() + 5
    while _t.time() < deadline and fake.windows[0].rect != big_windowed:
        _t.sleep(0.05)
    assert fake.windows[0].rect == big_windowed, fake.windows[0]
    print("remember + restore (normal): ok")


def test_restore_maximized_and_fighting_app(tmp):
    fake, clock = fresh(tmp)
    wm._layouts = {"excel.exe": {"state": "maximized", "rect": [20, 10, 1900, 1040]}}
    fake.windows = [Win(9, "excel.exe", "Book1", (300, 200, 1100, 800), False, False)]
    wm._place_worker("excel.exe", dict(wm._layouts["excel.exe"]))
    assert fake.windows[0].zoomed, "should be maximized again"
    assert not wm._placing, "placing flag must be cleared afterwards"

    fake, clock = fresh(tmp)
    layout = {"state": "normal", "rect": [20, 10, 1900, 1040]}
    fake.windows = [Win(10, "excel.exe", "Book1", (300, 200, 1100, 800), False, False)]
    fake.app_moves_window_to = (50, 50, 1000, 700)       # the app moves itself right after the first placement
    wm._place_worker("excel.exe", layout)
    assert fake.windows[0].rect == (20, 10, 1900, 1040), "must re-apply after the app moves it"
    assert sum(1 for e in fake.log if e[0] == "rect") == 2
    print("restore maximized + an app that fights back: ok")


def test_missing_monitor_and_timeout(tmp):
    fake, clock = fresh(tmp)
    off_screen = {"state": "normal", "rect": [3000, 100, 4800, 1000]}      # a monitor that's no longer connected
    fake.windows = [Win(11, "excel.exe", "Book1", (300, 200, 1100, 800), False, False)]
    wm._place_worker("excel.exe", off_screen)
    assert fake.windows[0].rect == (300, 200, 1100, 800), "must not move a window onto a missing monitor"
    fake, clock = fresh(tmp)
    wm._place_worker("excel.exe", {"state": "normal", "rect": [0, 0, 800, 600]})       # window never appears
    assert clock["t"] >= wm.FIND_TIMEOUT and not wm._placing
    print("missing monitor + never-appearing window: ok")


def test_config_exes():
    cfg = {"profiles": {"A": {"key_1": [{"type": "app", "value": "excel"}, {"type": "url", "value": "https://x.com"}],
                              "key_2": [{"type": "app", "value": "ms-teams:"}, {"type": "text", "value": "hi"}]},
                         "B": {"key_1": [{"type": "app", "value": r"C:\x\Outlook.exe"}]}}}
    assert wm.exes_for_config(cfg) == {"excel.exe", "outlook.exe"}
    print("exes_for_config: ok")


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as tmp:
        test_expected_exe()
        test_bring_back(tmp)
        test_remembers_and_restores(tmp)
        test_restore_maximized_and_fighting_app(tmp)
        test_missing_monitor_and_timeout(tmp)
        test_config_exes()
    print("\nall window_memory tests passed")
