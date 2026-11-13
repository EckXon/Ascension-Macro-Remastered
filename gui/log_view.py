import time
import tkinter as tk
from tkinter import scrolledtext, ttk

MODE_USER = 0
MODE_SYSTEM = 1
MODE_WARN = 2
MODE_ERROR = 3

MODE_LABELS = {
    MODE_USER: "[USER]",
    MODE_WARN: "[WARN]",
    MODE_ERROR: "[ERROR]",
}

_MODE_TAGS = {
    MODE_USER: "mode0",
    MODE_WARN: "mode2",
    MODE_ERROR: "mode3",
}

_MODE_COLORS = {
    "mode0": "green",
    "mode2": "dark goldenrod",
    "mode3": "red",
}

_FILTERS = (
    (MODE_USER, "User"),
    (MODE_SYSTEM, "System"),
    (MODE_WARN, "Warning"),
    (MODE_ERROR, "Error"),
)


def time_text():
    return time.strftime("%H:%M:%S")


def _line(stamp, message, mode):
    label = MODE_LABELS.get(mode)
    if label:
        return f"{stamp} {label} {message}\n"
    return f"{stamp} {message}\n"


class LogView:
    def __init__(self, parent):
        self.entries = []
        self.filter_var = tk.StringVar()
        self.mode_vars = {
            mode: tk.BooleanVar(value=True) for mode, _label in _FILTERS
        }

        filter_row = ttk.Frame(parent)
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="Filter:").pack(side="left")
        ttk.Entry(filter_row, textvariable=self.filter_var).pack(
            side="left", fill="x", expand=True, padx=(8, 12)
        )
        for mode, label in _FILTERS:
            ttk.Checkbutton(
                filter_row,
                text=label,
                variable=self.mode_vars[mode],
                command=self._render,
            ).pack(side="left", padx=(0, 8))

        self.log_text = scrolledtext.ScrolledText(parent, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)
        for tag, color in _MODE_COLORS.items():
            self.log_text.tag_configure(tag, foreground=color)
        ttk.Button(parent, text="Clear", command=self.clear).pack(
            anchor="e", pady=(8, 0)
        )
        self.filter_var.trace_add("write", lambda *_args: self._render())

    def append(self, message, mode=MODE_SYSTEM):
        entry = (time_text(), message, mode)
        self.entries.append(entry)
        if not self._matches(*entry):
            return
        self.log_text.configure(state="normal")
        self._insert_entry(*entry)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def clear(self):
        self.entries.clear()
        self._render()

    def _matches(self, stamp, message, mode):
        if not self._mode_enabled(mode):
            return False
        query = self.filter_var.get().strip().lower()
        if not query:
            return True
        return query in _line(stamp, message, mode).lower()

    def _mode_enabled(self, mode):
        var = self.mode_vars.get(mode)
        if var is None:
            return True
        return bool(var.get())

    def _insert_entry(self, stamp, message, mode):
        tag = _MODE_TAGS.get(mode)
        line = _line(stamp, message, mode)
        if tag:
            self.log_text.insert("end", line, tag)
        else:
            self.log_text.insert("end", line)

    def _render(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        for entry in self.entries:
            if self._matches(*entry):
                self._insert_entry(*entry)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
