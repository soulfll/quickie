"""
Talks back to the Quick-Key over its USB serial connection, so the little screen
can show the active profile and walk through what each key does. (Key presses go the other way, as ordinary
keyboard keys -- see listener.py. This link is only for the app -> device
direction.)

Protocol, one line of plain text per message (see src/link.cpp in the firmware):
    H\n                              "hello" -- the app just connected (ignored)
    P:<profile name>\n               the active profile (the idle screen)
    S:<title>|<line>|<line>|<line>\n a message that goes away after a few seconds
    A:<title>|<line>|<line>|<line>\n a message that stays until the next one
    C\n                              clear any message
    V:<percent>|<muted 0/1>\n        show the volume bar for a moment

Everything here is best-effort and runs in its own thread: if the Quick-Key
isn't plugged in, or the serial library is missing, the rest of the app works
exactly the same. It also finds the device by itself, so plugging the Quick-Key
in after the app is already open just works.
"""

import queue
import threading

from debuglog import debug

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # app still runs, just without the screen link
    serial = None
    list_ports = None

# The Teensy's USB vendor ID (PJRC). Teensy 4.0 is the only thing we expect
# to match; revisit if the product ever gets its own vendor ID.
TEENSY_VID = 0x16C0
BAUD = 115200
RETRY_SECONDS = 1.5
MAX_NAME = 20
MAX_LINE = 40         # characters per screen line


def clean_text(text: str, limit: int = MAX_LINE) -> str:
    """The screen's fonts are plain ASCII: anything else becomes '?', newlines
    become spaces, and '|' (which separates fields on the wire) becomes '/'."""
    out = "".join(c if 32 <= ord(c) < 127 else "?" for c in " ".join(str(text).split()))
    return out[:limit].replace("|", "/")


def clean_name(name: str) -> str:
    return clean_text(name, MAX_NAME)


def find_quick_key_port():
    if list_ports is None:
        return None
    for port in list_ports.comports():
        if port.vid == TEENSY_VID:
            return port.device
    return None


class DeviceLink:
    def __init__(self):
        self._active = ""            # the active profile
        self._lock = threading.Lock()
        self._dirty = False          # the active profile is waiting to be sent
        self._outbox = queue.Queue() # screen messages waiting to be sent
        self._stop = threading.Event()
        self._thread = None
        self.connected = False

    def start(self):
        if serial is None:
            print("[device_link] pyserial not installed -- screen link disabled")
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def set_profile(self, name: str):
        """Tell the device which profile is active. Safe to call from any
        thread, at any time, device or no device."""
        with self._lock:
            self._active = clean_name(name)
            self._dirty = True

    def show(self, title: str, lines=(), sticky: bool = False):
        """Put a message on the device's screen: a title and up to three
        lines. Normally it fades back to the profile after a few seconds;
        sticky=True keeps it up until the next message or clear() (for steps
        that wait for the user). Dropped if no device is connected -- these
        messages only matter at the moment they happen."""
        if not self.connected:
            return
        fields = [clean_text(title)] + [clean_text(l) for l in list(lines)[:3]]
        self._outbox.put(f"{'A' if sticky else 'S'}:{'|'.join(fields)}\n")

    def clear(self):
        if self.connected:
            self._outbox.put("C\n")

    def show_volume(self, percent: int, muted: bool):
        debug(f"show_volume({percent}, {muted}) connected={self.connected}")
        if self.connected:
            percent = max(0, min(100, int(percent)))
            self._outbox.put(f"V:{percent}|{1 if muted else 0}\n")

    # -- background thread -------------------------------------------------

    def _run(self):
        while not self._stop.is_set():
            port = find_quick_key_port()
            if port is None:
                self.connected = False
                self._stop.wait(RETRY_SECONDS)
                continue
            try:
                self._session(port)
            except Exception as e:  # unplugged mid-session, port busy, etc.
                print(f"[device_link] lost connection: {e}")
            self.connected = False
            self._stop.wait(RETRY_SECONDS)

    def _session(self, port):
        with serial.Serial(port, BAUD, timeout=0.1, write_timeout=1) as ser:
            self.connected = True
            debug(f"connected to {port}")
            ser.write(b"H\n")
            with self._lock:
                self._dirty = True   # always re-send everything on connect
            while not self._stop.is_set():
                with self._lock:
                    send = self._dirty
                    active = self._active
                    self._dirty = False
                if send and active:
                    ser.write(f"P:{active}\n".encode("ascii"))
                # Wait for the next message instead of sleeping, so one that
                # arrives goes out straight away (this loop was a source of lag).
                try:
                    message = self._outbox.get(timeout=0.02)
                except queue.Empty:
                    message = None
                while message is not None:
                    ser.write(message.encode("ascii"))
                    try:
                        message = self._outbox.get_nowait()
                    except queue.Empty:
                        message = None
                # The firmware also prints key presses for debugging; read
                # and drop them so that output can never back up and stall it.
                # Only if something is waiting, so this never blocks.
                if ser.in_waiting:
                    ser.read(ser.in_waiting)
