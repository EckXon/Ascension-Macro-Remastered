import tkinter as tk
from tkinter import ttk

from gui.fields import display, parse_number, parse_optional_int


class SettingsForm:
    def __init__(self, parent, on_save):
        self.user_id_var = tk.StringVar()
        self.display_name_var = tk.StringVar()
        self.private_server_url_var = tk.StringVar()
        self.place_id_var = tk.StringVar()
        self.check_interval_var = tk.StringVar()
        self.rejoin_interval_var = tk.StringVar()
        self.join_sequence_enabled_var = tk.BooleanVar(value=True)
        self.loop_sequence_interval_var = tk.StringVar()
        self.loop_sequence_enabled_var = tk.BooleanVar(value=True)

        fields = (
            ("User ID*", self.user_id_var, None),
            ("Display name", self.display_name_var, None),
            ("Private server URL", self.private_server_url_var, None),
            ("Place ID*", self.place_id_var, None),
            ("Check interval* (seconds)", self.check_interval_var, None),
            (
                "Rejoin interval* (seconds)",
                self.rejoin_interval_var,
                ("Join sequence", self.join_sequence_enabled_var),
            ),
            (
                "Loop sequence interval* (seconds)",
                self.loop_sequence_interval_var,
                ("Loop sequence", self.loop_sequence_enabled_var),
            ),
        )
        for row, (label, variable, toggle) in enumerate(fields):
            ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(parent, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=4)
            if toggle:
                toggle_text, toggle_var = toggle
                ttk.Checkbutton(parent, text=toggle_text, variable=toggle_var).grid(
                    row=row, column=2, sticky="w", padx=(12, 0), pady=4
                )
        parent.columnconfigure(1, weight=1)

        ttk.Button(parent, text="Save", command=on_save).grid(
            row=len(fields), column=1, sticky="e", pady=(12, 0)
        )

    def load(self, data):
        self.user_id_var.set(display(data["user_id"]))
        self.display_name_var.set(display(data["display_name"]))
        self.private_server_url_var.set(display(data["private_server_url"]))
        self.place_id_var.set(display(data["place_id"]))
        self.check_interval_var.set(display(data["check_interval"]))
        self.rejoin_interval_var.set(display(data["rejoin_interval"]))
        self.join_sequence_enabled_var.set(bool(data["join_sequence_enabled"]))
        self.loop_sequence_interval_var.set(display(data["loop_sequence_interval"]))
        self.loop_sequence_enabled_var.set(bool(data["loop_sequence_enabled"]))

    def read(self):
        return {
            "user_id": parse_optional_int(self.user_id_var.get(), "user_id"),
            "display_name": self.display_name() or None,
            "private_server_url": self.private_server_url_var.get().strip() or None,
            "place_id": parse_optional_int(self.place_id_var.get(), "place_id"),
            "check_interval": parse_number(
                self.check_interval_var.get(), "check_interval"
            ),
            "rejoin_interval": parse_number(
                self.rejoin_interval_var.get(), "rejoin_interval"
            ),
            "join_sequence_enabled": bool(self.join_sequence_enabled_var.get()),
            "loop_sequence_interval": parse_number(
                self.loop_sequence_interval_var.get(), "loop_sequence_interval"
            ),
            "loop_sequence_enabled": bool(self.loop_sequence_enabled_var.get()),
        }

    def display_name(self):
        return self.display_name_var.get().strip()

    def set_display_name(self, name):
        self.display_name_var.set(name)

    def user_id_text(self):
        return self.user_id_var.get()
