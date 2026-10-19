"""
Multi-select behavior shared by every list in the app.

With selectmode="extended", Tk gives Shift-click for a range and
Control-click to add or drop a single item. That's right on Windows, but on
a Mac people expect Command-click, and Tk doesn't bind it. This adds it,
using Tk's own toggle routine so it behaves exactly like Control-click does.
"""

import sys


def enable_command_click(listbox):
    if sys.platform != "darwin":
        return

    def toggle(event):
        index = listbox.index(f"@{event.x},{event.y}")
        listbox.tk.call("tk::ListboxBeginToggle", listbox, index)
        # "break" stops Tk's normal click handler from also running and
        # throwing away the rest of the selection.
        return "break"

    listbox.bind("<Command-Button-1>", toggle)
