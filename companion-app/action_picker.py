"""
The "what should this key do?" popup: shared by both ways of assigning a
slot (the manual "Add..." button in gui.py, and the assign-via-keypress flow
in main.py) so there's exactly one place that knows about the 3 action
types, instead of two copies that could drift apart.

Returns a list of action dicts -- {"type": "app"|"url"|"text", "value": str}
-- or an empty list if the user backed out at any point. See config.py for
where these get saved and config.action_label() for how they're displayed.

Important: this only adds a click at *assign* time. Pressing a physical key
at runtime is untouched -- still exactly one press, no matter which of the
3 types is behind it. That's the whole point.
"""

import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk

from app_scanner import filter_apps, find_installed_apps
from listbox_select import enable_command_click
from recorder import Recorder


def _browse_for_apps():
    """Fallback for an app that isn't in the list. Runs the OS's own file
    chooser, so it needs no extra libraries. Returns a list of paths.

    On macOS this goes through osascript instead of Tk's file dialog: Tk's
    shows .app bundles as folders (can open them, can't pick them) and
    attaches itself to our window as a sheet, so the window moved with it."""
    if sys.platform == "darwin":
        script = (
            'set picked to choose file of type {"com.apple.application-bundle"} '
            'with prompt "Choose app(s)" '
            'default location (POSIX file "/Applications") '
            'with multiple selections allowed\n'
            'set out to {}\n'
            'repeat with f in picked\n'
            '  set end of out to POSIX path of f\n'
            'end repeat\n'
            'set AppleScript\'s text item delimiters to linefeed\n'
            'return out as text'
        )
        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True,
            )
        except OSError:
            return []
        if result.returncode != 0:  # user hit Cancel (or osascript failed)
            return []
        return [line.strip().rstrip("/") for line in result.stdout.splitlines() if line.strip()]

    initialdir = None
    if sys.platform == "win32":
        start_menu = os.path.join(
            os.environ.get("ProgramData", r"C:\ProgramData"),
            "Microsoft", "Windows", "Start Menu", "Programs",
        )
        initialdir = start_menu if os.path.isdir(start_menu) else None
        filetypes = [("Applications", "*.exe *.lnk"), ("All files", "*.*")]
    else:
        filetypes = [("All files", "*")]
    return list(filedialog.askopenfilenames(
        title="Choose app(s)", initialdir=initialdir, filetypes=filetypes,
    ))


class _AppPickerDialog(tk.Toplevel):
    """Searchable list of installed apps (see app_scanner.py). Select one or
    several -- Shift-click for a range, Cmd-click (Mac) / Ctrl-click
    (Windows) to add or drop single ones -- then Add Selected."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Choose App(s)")
        self.result = []
        self._all_apps = find_installed_apps()
        self._shown = list(self._all_apps)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        ttk.Label(self, text="Search:").grid(row=0, column=0, sticky="w", padx=(12, 4), pady=(12, 4))
        self.query = tk.StringVar()
        self.query.trace_add("write", lambda *_: self._refilter())
        search = ttk.Entry(self, textvariable=self.query, width=40)
        search.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=(12, 4))

        frame = ttk.Frame(self)
        frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=4)
        self.listbox = tk.Listbox(
            frame, selectmode="extended", exportselection=False, height=14, width=46,
        )
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        enable_command_click(self.listbox)
        self.listbox.bind("<Double-Button-1>", lambda e: self._add_selected())

        mod = "Cmd" if sys.platform == "darwin" else "Ctrl"
        ttk.Label(
            self, foreground="gray",
            text=f"{mod}-click to pick several, Shift-click for a range.",
        ).grid(row=2, column=0, columnspan=2, sticky="w", padx=12)

        btns = ttk.Frame(self)
        btns.grid(row=3, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="Add Selected", command=self._add_selected).pack(side="left", padx=4)
        ttk.Button(btns, text="Browse for Other...", command=self._browse).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)
        self._refilter()
        search.focus_set()
        self.wait_window(self)

    def _refilter(self):
        self._shown = filter_apps(self._all_apps, self.query.get())
        self.listbox.delete(0, "end")
        for name, _path in self._shown:
            self.listbox.insert("end", name)

    def _add_selected(self):
        self.result = [self._shown[i][1] for i in self.listbox.curselection()]
        if self.result:
            self.destroy()

    def _browse(self):
        picked = _browse_for_apps()
        if picked:
            self.result = picked
            self.destroy()


def _pick_apps(parent):
    dialog = _AppPickerDialog(parent)
    return [{"type": "app", "value": p} for p in dialog.result]


def _pick_website(parent):
    url = simpledialog.askstring(
        "Add Website", "URL (e.g. mail.google.com):", parent=parent,
    )
    if not url:
        return []
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return [{"type": "url", "value": url}]


class _TextSnippetDialog(tk.Toplevel):
    """Multi-line text entry. simpledialog.askstring is single-line only,
    which doesn't work for a real signature / code block / canned reply."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Text Snippet")
        self.result = None
        self.transient(parent)
        self.grab_set()

        ttk.Label(self, text="Text to type when this key is pressed:").pack(
            anchor="w", padx=10, pady=(10, 4)
        )
        self.text = tk.Text(self, width=50, height=8)
        self.text.pack(padx=10, pady=(0, 10))
        self.text.focus_set()

        btns = ttk.Frame(self)
        btns.pack(pady=(0, 10))
        ttk.Button(btns, text="Save", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.wait_window(self)

    def _save(self):
        value = self.text.get("1.0", "end").rstrip("\n")
        if value:
            self.result = value
        self.destroy()


def _pick_text(parent):
    dialog = _TextSnippetDialog(parent)
    if dialog.result:
        return [{"type": "text", "value": dialog.result}]
    return []


class _RecordDialog(tk.Toplevel):
    """Start/stop recorder for a keystroke macro. Recording is global (works
    while you're typing in other apps), so it's stopped with a mouse click on
    this window -- no keystroke is needed to end it, and none gets recorded
    by mistake."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Record Keystrokes")
        self.result = None
        self._recorder = Recorder()
        self.transient(parent)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.info = tk.StringVar(
            value="Click Start, then do your keystrokes in any app.\n"
                  "Come back here and click Stop when you're done.\n\n"
                  "Don't type passwords while recording -- every key is saved."
        )
        ttk.Label(self, textvariable=self.info, justify="left").pack(
            padx=20, pady=(16, 10)
        )

        btns = ttk.Frame(self)
        btns.pack(pady=(0, 16))
        self.start_btn = ttk.Button(btns, text="Start Recording", command=self._start)
        self.start_btn.pack(side="left", padx=4)
        self.stop_btn = ttk.Button(
            btns, text="Stop & Save", command=self._stop, state="disabled",
        )
        self.stop_btn.pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="left", padx=4)

        self.wait_window(self)

    def _start(self):
        self._recorder.start()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._tick()

    def _tick(self):
        if self._recorder.recording:
            presses = sum(1 for e in self._recorder.events if e["action"] == "down")
            self.info.set(f"RECORDING...  {presses} keystrokes so far\n\n"
                          "Do your keystrokes, then click Stop & Save here.")
            self.after(200, self._tick)

    def _stop(self):
        events = self._recorder.stop()
        if any(e["action"] == "down" for e in events):
            self.result = events
        self.destroy()

    def _cancel(self):
        if self._recorder.recording:
            self._recorder.stop()
        self.destroy()


def _pick_macro(parent):
    dialog = _RecordDialog(parent)
    if dialog.result:
        return [{"type": "macro", "value": dialog.result}]
    return []


class _TypeChooser(tk.Toplevel):
    """The one extra click this whole design costs: app vs website vs text."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Add Action")
        self.choice = None
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        ttk.Label(self, text="What should this key do?").pack(padx=24, pady=(16, 8))
        for label, key in [
            ("Open App(s)", "app"),
            ("Open Website", "url"),
            ("Type Text Snippet", "text"),
            ("Record Keystrokes", "macro"),
        ]:
            ttk.Button(
                self, text=label, width=28,
                command=lambda k=key: self._choose(k),
            ).pack(padx=24, pady=4)
        ttk.Button(self, text="Cancel", command=self.destroy).pack(pady=(8, 16))

        self.wait_window(self)

    def _choose(self, key):
        self.choice = key
        self.destroy()


def prompt_for_actions(parent):
    """Shows the type chooser, then whichever follow-up picker matches.
    Always returns a list (possibly empty if cancelled at any step) --
    never None -- so callers don't need a separate null check."""
    chooser = _TypeChooser(parent)
    if chooser.choice == "app":
        return _pick_apps(parent)
    elif chooser.choice == "url":
        return _pick_website(parent)
    elif chooser.choice == "text":
        return _pick_text(parent)
    elif chooser.choice == "macro":
        return _pick_macro(parent)
    return []
