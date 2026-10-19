"""
Keeps the Quick-Key's volume bar honest.

The dial only sends "volume up" / "volume down" / "mute" keys -- it has no idea
what the computer's volume actually is. So whenever one of those keys is seen
(from the dial or any keyboard), we ask the operating system for the real
volume and hand it to a callback, which sends it to the device's screen. That
way the bar always matches reality, whatever changed the volume.

  - macOS:   asks AppleScript for the volume settings (nothing to install).
  - Windows: uses pycaw (a small library over the Windows audio API). If it
             isn't installed, or anything goes wrong, we just return None and
             the bar is skipped -- the dial itself still works, since it's a
             plain keyboard media key.
"""

import re
import subprocess
import sys
import threading

from debuglog import debug


def _mac_volume_osascript():
    """The slow, simple way (~130 ms, because it starts a process). Kept as a
    fallback in case the direct audio query below isn't available."""
    result = subprocess.run(
        ["osascript", "-e", "get volume settings"],
        capture_output=True, text=True, timeout=3,
    )
    match = re.search(r"output volume:(\d+)", result.stdout)
    if not match:
        return None
    return int(match.group(1)), "output muted:true" in result.stdout


_core_audio = None


def _fourcc(code: str) -> int:
    return int.from_bytes(code.encode("ascii"), "big")


def _mac_volume():
    """Asks macOS's audio system directly (CoreAudio, through ctypes -- nothing
    to install). It answers in microseconds, which is what makes the volume bar
    feel instant. Falls back to AppleScript if anything is unavailable."""
    import ctypes
    global _core_audio
    try:
        if _core_audio is None:
            lib = ctypes.CDLL("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")

            class Address(ctypes.Structure):
                _fields_ = [("selector", ctypes.c_uint32), ("scope", ctypes.c_uint32),
                            ("element", ctypes.c_uint32)]

            lib.AudioObjectGetPropertyData.argtypes = [
                ctypes.c_uint32, ctypes.POINTER(Address), ctypes.c_uint32, ctypes.c_void_p,
                ctypes.POINTER(ctypes.c_uint32), ctypes.c_void_p]
            lib.AudioObjectGetPropertyData.restype = ctypes.c_int32
            _core_audio = (lib, Address)
        lib, Address = _core_audio

        def get(obj, selector, scope, ctype):
            addr = Address(_fourcc(selector), _fourcc(scope), 0)
            value = ctype()
            size = ctypes.c_uint32(ctypes.sizeof(value))
            status = lib.AudioObjectGetPropertyData(
                obj, ctypes.byref(addr), 0, None, ctypes.byref(size), ctypes.byref(value))
            return value.value if status == 0 else None

        device = get(1, "dOut", "glob", ctypes.c_uint32)       # the default output device
        if device:
            volume = get(device, "vmvc", "outp", ctypes.c_float)   # the system "main volume"
            muted = get(device, "mute", "outp", ctypes.c_uint32)
            if volume is not None and muted is not None:
                return round(volume * 100), bool(muted)
    except Exception as e:
        debug(f"fast volume read unavailable ({e}); using AppleScript")
    return _mac_volume_osascript()


def _windows_volume():
    try:
        import comtypes
        from pycaw.pycaw import AudioUtilities
    except ImportError:
        return None
    comtypes.CoInitialize()    # Windows audio is COM, which must be set up per thread
    try:
        speakers = AudioUtilities.GetSpeakers()
        endpoint = getattr(speakers, "EndpointVolume", None)    # newer pycaw hands this over directly
        if endpoint is None:                                     # older pycaw: activate it ourselves
            from ctypes import POINTER, cast
            from pycaw.pycaw import IAudioEndpointVolume
            interface = speakers.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
            endpoint = cast(interface, POINTER(IAudioEndpointVolume))
        return round(endpoint.GetMasterVolumeLevelScalar() * 100), bool(endpoint.GetMute())
    finally:
        comtypes.CoUninitialize()


def get_volume():
    """Returns (percent 0-100, muted) or None if it can't be read."""
    try:
        if sys.platform == "darwin":
            return _mac_volume()
        if sys.platform == "win32":
            return _windows_volume()
    except Exception as e:
        print(f"[volume_sync] couldn't read the volume: {e}")
    return None


class VolumeWatcher:
    """Call notify() every time a volume key is seen. The first key triggers a
    read almost immediately, so the bar moves right away; keys that keep
    arriving (a fast turn of the dial) keep it updating as they go. A final
    "settling" read after the last key catches anything the OS applied late,
    so the bar always ends on the true value. Results go to
    on_volume(percent, muted)."""

    def __init__(self, on_volume, delay: float = 0.03, settle: float = 0.15):
        self._on_volume = on_volume
        self._delay = delay      # lets the OS finish applying the change first
        self._settle = settle
        self._timer = None
        self._settle_timer = None
        self._lock = threading.Lock()

    def notify(self):
        with self._lock:
            if self._timer is None:
                self._timer = threading.Timer(self._delay, self._read)
                self._timer.daemon = True
                self._timer.start()
            if self._settle_timer is not None:
                self._settle_timer.cancel()
            self._settle_timer = threading.Timer(self._settle, self._read_final)
            self._settle_timer.daemon = True
            self._settle_timer.start()

    def _read(self):
        with self._lock:
            self._timer = None   # keys that arrive from now on schedule a fresh read
        self._read_final()

    def _read_final(self):
        result = get_volume()
        debug(f"volume read: {result}")
        if result is not None:
            self._on_volume(*result)
