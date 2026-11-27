"""
The dialog for the Quick-Key's "unlock" key (Key 7).

That key types a stored password itself, as a real USB keyboard, which is the
only way to type at the Windows sign-in screen (Windows won't let any program
on the PC see keys on, or type into, that screen). The password is typed here,
sent over the USB link, and kept inside the Quick-Key.

ask_unlock_password() returns:
    a non-empty string  -> store this password
    ""                  -> clear the stored password (Key 7 becomes a normal key)
    None                -> cancelled
"""

import tkinter as tk
from tkinter import ttk

MAX_LEN = 63    # keep in step with UNLOCK_MAX_LEN in src/unlock.h


def typeable(password: str) -> bool:
    """The Quick-Key types plain printable ASCII, up to MAX_LEN characters."""
    return 0 < len(password) <= MAX_LEN and all(32 <= ord(c) < 127 for c in password)


class _UnlockDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Unlock Password (Key 7)")
        self.result = None
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)

        self.first, self.again = tk.StringVar(), tk.StringVar()
        ttk.Label(
            self, justify="left",
            text="Key 7 will type this password by itself, like a keyboard.\n"
                 "That works at the Windows sign-in screen too.",
        ).pack(anchor="w", padx=14, pady=(14, 8))
        ttk.Label(self, text="Password:").pack(anchor="w", padx=14)
        first = ttk.Entry(self, textvariable=self.first, show="•", width=36)
        first.pack(padx=14, pady=(2, 8))
        ttk.Label(self, text="Again, to be sure:").pack(anchor="w", padx=14)
        ttk.Entry(self, textvariable=self.again, show="•", width=36).pack(padx=14, pady=(2, 8))
        ttk.Label(
            self, foreground="#8a5a00", justify="left",
            text="It is stored as plain text inside the Quick-Key, so anyone who\n"
                 "has the device could read it. Use a demo password, not one\n"
                 "that matters. Letters, numbers and symbols, up to 63 characters.",
        ).pack(anchor="w", padx=14, pady=(0, 4))
        self.error = ttk.Label(self, foreground="#b00020")
        self.error.pack(anchor="w", padx=14)
        first.focus_set()

        btns = ttk.Frame(self)
        btns.pack(pady=(4, 14))
        ttk.Button(btns, text="Save to Quick-Key", command=self._save).pack(side="left", padx=4)
        ttk.Button(btns, text="Clear stored password", command=self._clear).pack(side="left", padx=4)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        self.bind("<Return>", lambda e: self._save())

        self.wait_window(self)

    def _save(self):
        pw = self.first.get()
        if not pw:
            self.error.config(text="Type a password first.")
        elif pw != self.again.get():
            self.error.config(text="The two entries don't match.")
        elif not typeable(pw):
            self.error.config(text=f"Use plain letters, numbers and symbols, up to {MAX_LEN} characters.")
        else:
            self.result = pw
            self.destroy()

    def _clear(self):
        self.result = ""
        self.destroy()


def ask_unlock_password(parent):
    return _UnlockDialog(parent).result
