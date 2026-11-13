import tkinter as tk
from tkinter import ttk

import config
from gui.fields import (
    ACTION_LABELS,
    ACTIONS_BY_LABEL,
    display,
    parse_number,
    parse_optional_int,
)


class StepDialog(tk.Toplevel):
    def __init__(self, master, step=None, parse_step=config.parse_join_sequence):
        super().__init__(master)
        self.title("Edit step" if step else "Add step")
        self.resizable(False, False)
        self.result = None
        self.parse_step = parse_step
        self.transient(master)

        kind = step[0] if step else "wait"
        self.action_var = tk.StringVar(value=ACTION_LABELS[kind])
        self.seconds_var = tk.StringVar(
            value=display(step[1]) if step and kind == "wait" else ""
        )
        self.x_var = tk.StringVar(
            value=display(step[1]) if step and kind == "click" else ""
        )
        self.y_var = tk.StringVar(
            value=display(step[2]) if step and kind == "click" else ""
        )
        self.click_duration_var = tk.StringVar(
            value=display(step[3]) if step and kind == "click" and len(step) > 3 else ""
        )
        self.key_var = tk.StringVar(value=step[1] if step and kind == "key" else "")
        self.hotkey_var = tk.StringVar(
            value="+".join(step[1:]) if step and kind == "hotkey" else ""
        )
        self.error_var = tk.StringVar()

        frame = ttk.Frame(self, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        ttk.Label(frame, text="Action").grid(row=0, column=0, sticky="w")
        action = ttk.Combobox(
            frame,
            textvariable=self.action_var,
            values=list(ACTION_LABELS.values()),
            state="readonly",
            width=24,
        )
        action.grid(row=0, column=1, sticky="ew", padx=(12, 0))
        action.bind("<<ComboboxSelected>>", lambda _event: self._show_fields())

        self.fields = ttk.Frame(frame)
        self.fields.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Label(frame, textvariable=self.error_var, wraplength=280).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(8, 0)
        )
        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(buttons, text="OK", command=self._ok).pack(side="right", padx=(0, 8))

        self._show_fields()
        self.bind("<Escape>", lambda _event: self._cancel())
        self.bind("<Return>", lambda _event: self._ok())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.grab_set()
        self.wait_window()

    def _show_fields(self):
        for child in self.fields.winfo_children():
            child.destroy()
        kind = ACTIONS_BY_LABEL[self.action_var.get()]
        if kind == "wait":
            rows = (("Seconds", self.seconds_var),)
        elif kind == "click":
            rows = (
                ("X", self.x_var),
                ("Y", self.y_var),
                ("Duration (seconds)", self.click_duration_var),
            )
        elif kind == "key":
            rows = (("Key", self.key_var),)
        else:
            rows = (("Keys", self.hotkey_var),)
        for row, (label, variable) in enumerate(rows):
            ttk.Label(self.fields, text=label).grid(
                row=row, column=0, sticky="w", pady=4
            )
            ttk.Entry(self.fields, textvariable=variable, width=24).grid(
                row=row, column=1, sticky="ew", padx=(12, 0), pady=4
            )
        self.fields.columnconfigure(1, weight=1)

    def _ok(self):
        kind = ACTIONS_BY_LABEL[self.action_var.get()]
        try:
            if kind == "wait":
                seconds = parse_number(self.seconds_var.get(), "seconds")
                if seconds < 0:
                    raise ValueError("seconds must be 0 or greater")
                step = ["wait", seconds]
            elif kind == "click":
                x = parse_optional_int(self.x_var.get(), "x")
                y = parse_optional_int(self.y_var.get(), "y")
                if x is None or y is None:
                    raise ValueError("x and y are required")
                duration_text = self.click_duration_var.get().strip()
                duration = 0
                if duration_text:
                    duration = parse_number(duration_text, "duration")
                    if duration < 0:
                        raise ValueError("duration must be 0 or greater")
                step = ["click", x, y]
                if duration:
                    step.append(duration)
            elif kind == "key":
                step = ["key", self.key_var.get()]
            else:
                keys = [
                    part.strip()
                    for part in self.hotkey_var.get().split("+")
                    if part.strip()
                ]
                step = ["hotkey", *keys]
            self.result = self.parse_step([step])[0]
        except (TypeError, ValueError) as exc:
            self.error_var.set(str(exc))
            return
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
