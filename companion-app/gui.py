"""
Tkinter UI: a profile selector up top, then one row per key,
each with a list of assigned actions (apps, websites, or text snippets --
see action_picker.py and config.py) and Add/Remove buttons. Tkinter ships
with Python so there's nothing extra to install for the UI itself.
"""

import sys
import tkinter as tk
from tkinter import simpledialog, ttk

import config as config_store
from action_picker import prompt_for_actions
from keymap import SLOT_ORDER, SLOT_LABELS
from listbox_select import enable_command_click

PENDING_COLOR = "#b58900"  # amber -- marks an unconfirmed assignment


class QuickKeyGUI:
    def __init__(self, root, slots, profile_names, active_profile,
                 on_change, on_profile_change, on_new_profile, on_assign_clicked,
                 on_unlock_clicked=None):
        self.root = root
        self.slots = slots  # live dict for the *active* profile: slot -> [actions]
        self.on_change = on_change              # called after any manual edit
        self.on_profile_change = on_profile_change  # called with new profile name
        self.on_new_profile = on_new_profile        # called with new profile name
        self.on_assign_clicked = on_assign_clicked  # called when "Assign via Key Press" clicked
        self.on_unlock_clicked = on_unlock_clicked  # called when "Unlock Password" clicked
        self.listboxes = {}

        root.title("Quick-Key")
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
        if on_unlock_clicked is not None:
            ttk.Button(top, text="Unlock Password...", command=on_unlock_clicked).pack(side="right", padx=(0, 6))

        # -- status line -------------------------------------------------------
        self.status_var = tk.StringVar(value="Waiting for a key press...")
        status_label = ttk.Label(root, textvariable=self.status_var, foreground="gray")
        status_label.pack(fill="x", padx=10, pady=(6, 0))
        mod = "Cmd" if sys.platform == "darwin" else "Ctrl"
        ttk.Label(
            root, foreground="gray",
            text=f"Tip: {mod}-click to select several items in a list, then Remove Selected.",
        ).pack(fill="x", padx=10)

        # -- per-slot rows (in a scrollable area: all 8 rows never fit at once) ---
        container = ttk.Frame(root)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        background = ttk.Style().lookup("TFrame", "background") or root.cget("bg")
        self._canvas = tk.Canvas(container, highlightthickness=0, borderwidth=0,
                                 background=background, yscrollincrement=24)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        rows = ttk.Frame(self._canvas)
        rows_window = self._canvas.create_window((0, 0), window=rows, anchor="nw")
        # Keep the scrollable height matched to the rows, and the rows as wide as the window.
        rows.bind("<Configure>", lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        self._canvas.bind("<Configure>", lambda e: self._canvas.itemconfigure(rows_window, width=e.width))

        # Mouse wheel / trackpad scrolling (Windows, macOS and Linux differ).
        root.bind_all("<MouseWheel>", self._on_mousewheel)
        root.bind_all("<Button-4>", self._on_mousewheel)
        root.bind_all("<Button-5>", self._on_mousewheel)

        for slot in SLOT_ORDER:
            self._build_row(rows, slot)

    def _on_mousewheel(self, event):
        try:
            if event.widget.winfo_toplevel() is not self.root:
                return                      # a pop-up dialog, not the main window
        except (AttributeError, tk.TclError):
            return
        if self._canvas.yview() == (0.0, 1.0):
            return                          # everything already fits
        if isinstance(event.widget, tk.Listbox) and event.widget.yview() != (0.0, 1.0):
            return                          # that list has its own overflow: let it scroll
        if event.num == 4:
            step = -2
        elif event.num == 5:
            step = 2
        elif sys.platform == "darwin":
            step = -event.delta             # macOS reports small, already-scaled steps
        else:
            step = -int(event.delta / 120) * 2   # Windows: 120 per notch
        if step:
            self._canvas.yview_scroll(step, "units")

    # -- row construction --------------------------------------------------

    def _build_row(self, parent, slot):
        frame = ttk.LabelFrame(parent, text=SLOT_LABELS[slot])
        frame.pack(fill="x", pady=4)

        # extended = Shift-click for a range, Ctrl-click (Cmd-click on Mac)
        # to pick several. exportselection=False keeps one row's selection
        # from being cleared when you click in a different row's list.
        listbox = tk.Listbox(frame, height=3, selectmode="extended", exportselection=False)
        enable_command_click(listbox)
        listbox.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)
        self.listboxes[slot] = listbox
        self.refresh_slot(slot)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side="right", padx=6, pady=6)

        add_btn = ttk.Button(btn_frame, text="Add...",
                              command=lambda s=slot: self._add_action(s))
        add_btn.pack(fill="x", pady=(0, 4))

        remove_btn = ttk.Button(btn_frame, text="Remove Selected",
                                 command=lambda s=slot: self._remove_selected(s))
        remove_btn.pack(fill="x")

    # -- manual (mouse-driven) add/remove -----------------------------------

    def _add_action(self, slot):
        actions = prompt_for_actions(self.root)
        if not actions:
            return
        self.slots.setdefault(slot, [])
        changed = False
        for action in actions:
            if action not in self.slots[slot]:
                self.slots[slot].append(action)
                changed = True
        if changed:
            self.refresh_slot(slot)
            self.on_change()

    def _remove_selected(self, slot):
        listbox = self.listboxes[slot]
        selection = listbox.curselection()
        if not selection:
            return
        actions = self.slots.get(slot, [])
        # Delete from the highest index down so earlier removals don't
        # shift the positions of the ones still to go.
        for index in sorted(selection, reverse=True):
            if 0 <= index < len(actions):
                del actions[index]
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

    def add_pending(self, slot, actions):
        """Show not-yet-confirmed entries in amber until confirmed/cancelled."""
        listbox = self.listboxes[slot]
        for action in actions:
            idx = listbox.size()
            listbox.insert("end", f"⏳ {config_store.action_label(action)}  (press key again to confirm)")
            listbox.itemconfig(idx, fg=PENDING_COLOR)

    def confirm_pending(self, slot):
        self.refresh_slot(slot)  # self.slots already has the real entries by now

    def cancel_pending(self, slot):
        self.refresh_slot(slot)  # drops the amber preview; self.slots was never touched

    # -- shared helpers -------------------------------------------------------

    def refresh_slot(self, slot):
        listbox = self.listboxes[slot]
        listbox.delete(0, "end")
        for action in self.slots.get(slot, []):
            listbox.insert("end", config_store.action_label(action))

    def set_status(self, text: str):
        self.status_var.set(text)
