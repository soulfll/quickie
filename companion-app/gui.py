"""
Tkinter UI: one row per key/encoder slot, each with a list of assigned app
paths and Add/Remove buttons. Tkinter ships with Python so there's nothing
extra to install for the UI itself.
"""

import tkinter as tk
from tkinter import filedialog, ttk

from keymap import SLOT_ORDER, SLOT_LABELS


class QuickieGUI:
    def __init__(self, root, config, on_change):
        self.root = root
        self.config = config
        self.on_change = on_change  # called with (slot, updated config) after any edit
        self.listboxes = {}

        root.title("Quickie")
        root.geometry("520x520")

        self.status_var = tk.StringVar(value="Waiting for a key press...")
        status_label = ttk.Label(root, textvariable=self.status_var, foreground="gray")
        status_label.pack(fill="x", padx=10, pady=(10, 0))

        container = ttk.Frame(root)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        for slot in SLOT_ORDER:
            self._build_row(container, slot)

    def _build_row(self, parent, slot):
        frame = ttk.LabelFrame(parent, text=SLOT_LABELS[slot])
        frame.pack(fill="x", pady=4)

        listbox = tk.Listbox(frame, height=3)
        listbox.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        self.listboxes[slot] = listbox
        for path in self.config.get(slot, []):
            listbox.insert("end", path)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="right", padx=6, pady=6)

        add_btn = ttk.Button(btn_frame, text="Add App...",
                              command=lambda s=slot: self._add_app(s))
        add_btn.pack(fill="x", pady=(0, 4))

        remove_btn = ttk.Button(btn_frame, text="Remove Selected",
                                 command=lambda s=slot: self._remove_selected(s))
        remove_btn.pack(fill="x")

    def _add_app(self, slot):
        path = filedialog.askopenfilename(title=f"Choose app for {SLOT_LABELS[slot]}")
        if not path:
            return
        self.config.setdefault(slot, [])
        if path not in self.config[slot]:
            self.config[slot].append(path)
            self.listboxes[slot].insert("end", path)
            self.on_change(slot, self.config)

    def _remove_selected(self, slot):
        listbox = self.listboxes[slot]
        selection = listbox.curselection()
        if not selection:
            return
        index = selection[0]
        path = listbox.get(index)
        listbox.delete(index)
        if slot in self.config and path in self.config[slot]:
            self.config[slot].remove(path)
        self.on_change(slot, self.config)

    def set_status(self, text: str):
        self.status_var.set(text)
