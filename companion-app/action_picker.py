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
import sys
import tkinter as tk
from tkinter import filedialog, simpledialog, ttk


def _app_filetypes():
    if sys.platform == "win32":
        return [("Applications", "*.exe *.lnk"), ("All files", "*.*")]
    elif sys.platform == "darwin":
        return [("Applications", "*.app"), ("All files", "*")]
    return [("All files", "*")]


def _app_initialdir():
    """Point straight at the folder full of clean, icon-friendly shortcuts
    instead of leaving the user to dig through C:\\ or /. On Windows this is
    the exact same list the Start Menu itself shows -- the closest thing
    Windows has to macOS's tidy /Applications."""
    if sys.platform == "win32":
        start_menu = os.path.join(
            os.environ.get("ProgramData", r"C:\ProgramData"),
            "Microsoft", "Windows", "Start Menu", "Programs",
        )
        return start_menu if os.path.isdir(start_menu) else None
    elif sys.platform == "darwin":
        return "/Applications"
    return None


def _pick_apps(parent):
    paths = filedialog.askopenfilenames(
        parent=parent,
        title="Choose app(s)",
        initialdir=_app_initialdir(),
        filetypes=_app_filetypes(),
    )
    return [{"type": "app", "value": p} for p in paths]


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
    return []
