"""
Tkinter UI: a profile selector up top, then one row per key/encoder slot,
each with a list of assigned app paths and Add/Remove buttons. Tkinter ships
with Python so there's nothing extra to install for the UI itself.
"""

import tkinter as tk
from tkinter import filedialog, simpledialog, ttk

from keymap import SLOT_ORDER, SLOT_LABELS

PENDING_COLOR = "#b58900"  # amber -- marks an unconfirmed assignment


class QuickieGUI:
    def __init__(self, root, slots, profile_names, active_profile,
                 on_change, on_profile_change, on_new_profile, on_assign_clicked):
        self.root = root
        self.slots = slots  # live dict for the *active* profile: slot -> [paths]
        self.on_change = on_change              # called after any manual edit
        self.on_profile_change = on_profile_change  # called with new profile name
        self.on_new_profile = on_new_profile        # called with new profile name
        self.on_assign_clicked = on_assign_clicked  # called when "Assign via Key Press" clicked
        self.listboxes = {}

        root.title("Quickie")
        root.geometry("560x600")

        # -- top bar: profile selector + assign-by-keypress ------------------
        top = ttk.Frame(root)
        top.pack(fill="x", padx=10, pady=(10, 0))

        ttk.Label(top, text="Profile:").pack(side="left")
        self.profile_var = tk.StringVar(value=active_profile)
        self.profile_combo = ttk.Combobox(
            top, textvariable=self.profile_var, values=profile_names,
            state="readonly", width=18,
        )
        self.profile_combo.pack(side="left", padx=(4, 8))
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_selected)

        ttk.Button(top, text="New Profile...", command=self._new_profile).pack(side="left")

        self.assign_btn = ttk.Button(
            top, text="Assign via Key Press...", command=self._assign_clicked,
        )
        self.assign_btn.pack(side="right")

        # -- status line -------------------------------------------------------
        self.status_var = tk.StringVar(value="Waiting for a key press...")
        status_label = ttk.Label(root, textvariable=self.status_var, foreground="gray")
        status_label.pack(fill="x", padx=10, pady=(6, 0))

        # -- per-slot rows -------------------------------------------------------
        container = ttk.Frame(root)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        for slot in SLOT_ORDER:
            self._build_row(container, slot)

    # -- row construction --------------------------------------------------

    def _build_row(self, parent, slot):
        frame = ttk.LabelFrame(parent, text=SLOT_LABELS[slot])
        frame.pack(fill="x", pady=4)

        listbox = tk.Listbox(frame, height=3)
        listbox.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        self.listboxes[slot] = listbox
        self.refresh_slot(slot)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="right", padx=6, pady=6)

        add_btn = ttk.Button(btn_frame, text="Add App...",
                              command=lambda s=slot: self._add_app(s))
        add_btn.pack(fill="x", pady=(0, 4))

        remove_btn = ttk.Button(btn_frame, text="Remove Selected",
                                 command=lambda s=slot: self._remove_selected(s))
        remove_btn.pack(fill="x")

    # -- manual (mouse-driven) add/remove -----------------------------------

    def _add_app(self, slot):
        path = filedialog.askopenfilename(title=f"Choose app for {SLOT_LABELS[slot]}")
        if not path:
            return
        self.slots.setdefault(slot, [])
        if path not in self.slots[slot]:
            self.slots[slot].append(path)
            self.refresh_slot(slot)
            self.on_change()

    def _remove_selected(self, slot):
        listbox = self.listboxes[slot]
        selection = listbox.curselection()
        if not selection:
            return
        path = listbox.get(selection[0])
        if slot in self.slots and path in self.slots[slot]:
            self.slots[slot].remove(path)
            self.refresh_slot(slot)
            self.on_change()

    # -- profile controls ----------------------------------------------------

    def _on_profile_selected(self, event=None):
        self.on_profile_change(self.profile_var.get())

    def _new_profile(self):
        name = simpledialog.askstring("New Profile", "Profile name:", parent=self.root)
        if name:
            self.on_new_profile(name)

    def set_profile_list(self, names, active):
        self.profile_combo["values"] = names
        self.profile_var.set(active)

    def reload_slots(self, slots):
        """Swap in a different profile's slot dict and redraw every row."""
        self.slots = slots
        for slot in SLOT_ORDER:
            self.refresh_slot(slot)

    # -- assign-via-keypress (learn mode) ------------------------------------

    def _assign_clicked(self):
        self.on_assign_clicked()

    def set_assign_enabled(self, enabled: bool):
        self.assign_btn.config(state="normal" if enabled else "disabled")

    def add_pending(self, slot, paths):
        """Show not-yet-confirmed entries in amber until confirmed/cancelled."""
        listbox = self.listboxes[slot]
        for path in paths:
            idx = listbox.size()
            listbox.insert("end", f"⏳ {path}  (press key again to confirm)")
            listbox.itemconfig(idx, fg=PENDING_COLOR)

    def confirm_pending(self, slot):
        self.refresh_slot(slot)  # self.slots already has the real entries by now

    def cancel_pending(self, slot):
        self.refresh_slot(slot)  # drops the amber preview; self.slots was never touched

    # -- shared helpers -------------------------------------------------------

    def refresh_slot(self, slot):
        listbox = self.listboxes[slot]
        listbox.delete(0, "end")
        for path in self.slots.get(slot, []):
            listbox.insert("end", path)

    def set_status(self, text: str):
        self.status_var.set(text)
