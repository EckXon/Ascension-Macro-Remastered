import tkinter as tk
from tkinter import ttk

from gui.fields import step_text
from gui.step_dialog import StepDialog


class SequenceEditor:
    def __init__(self, parent, on_save, on_log, on_toggle_coords, parse_step, description):
        self.parent = parent
        self.on_save = on_save
        self.on_log = on_log
        self.parse_step = parse_step
        self.steps = []

        ttk.Label(parent, text=description, wraplength=880).pack(anchor="w")
        coord_row = ttk.Frame(parent)
        coord_row.pack(fill="x", pady=(4, 0))
        ttk.Label(
            coord_row,
            text="Coordinates are pixels inside the Roblox window.",
        ).pack(side="left")
        coord_button = ttk.Button(
            coord_row,
            text="Show coordinates",
            command=lambda: on_toggle_coords(coord_button),
        )
        coord_button.pack(side="right")
        body = ttk.Frame(parent)
        body.pack(fill="both", expand=True, pady=(8, 0))
        scroll = ttk.Scrollbar(body, orient="vertical")
        self.step_list = tk.Listbox(
            body, activestyle="dotbox", yscrollcommand=scroll.set, exportselection=False
        )
        scroll.configure(command=self.step_list.yview)
        self.step_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        step_buttons = ttk.Frame(parent)
        step_buttons.pack(fill="x", pady=(8, 0))
        for label, command in (
            ("Add", self.on_add_step),
            ("Edit", self.on_edit_step),
            ("Remove", self.on_remove_step),
            ("Up", self.on_move_step_up),
            ("Down", self.on_move_step_down),
        ):
            ttk.Button(step_buttons, text=label, command=command).pack(
                side="left", padx=(0, 8)
            )
        ttk.Button(step_buttons, text="Save", command=on_save).pack(side="right")

    def set_steps(self, steps):
        self.steps = list(steps)
        self.refresh()

    def refresh(self, select=None):
        self.step_list.delete(0, "end")
        for step in self.steps:
            self.step_list.insert("end", step_text(step))
        if select is None or not self.steps:
            return
        index = max(0, min(select, len(self.steps) - 1))
        self.step_list.selection_set(index)
        self.step_list.activate(index)
        self.step_list.see(index)

    def _selected_index(self):
        selected = self.step_list.curselection()
        if not selected:
            self.on_log("Select a step first.")
            return None
        return selected[0]

    def on_add_step(self):
        dialog = StepDialog(self.parent.winfo_toplevel(), parse_step=self.parse_step)
        if dialog.result is None:
            return
        self.steps.append(dialog.result)
        self.refresh(len(self.steps) - 1)

    def on_edit_step(self):
        index = self._selected_index()
        if index is None:
            return
        dialog = StepDialog(
            self.parent.winfo_toplevel(),
            self.steps[index],
            parse_step=self.parse_step,
        )
        if dialog.result is None:
            return
        self.steps[index] = dialog.result
        self.refresh(index)

    def on_remove_step(self):
        index = self._selected_index()
        if index is None:
            return
        del self.steps[index]
        self.refresh(min(index, len(self.steps) - 1))

    def on_move_step_up(self):
        self._move_step(-1)

    def on_move_step_down(self):
        self._move_step(1)

    def _move_step(self, offset):
        index = self._selected_index()
        if index is None:
            return
        target = index + offset
        if target < 0 or target >= len(self.steps):
            return
        self.steps[index], self.steps[target] = self.steps[target], self.steps[index]
        self.refresh(target)
