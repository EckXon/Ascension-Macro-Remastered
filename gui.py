import queue
import time
import tkinter as tk
from tkinter import scrolledtext, ttk

import config


def _display(value):
    if value is None:
        return ""
    return str(value)


def _parse_optional_int(text, name):
    text = text.strip()
    if not text:
        return None
    digits = text[1:] if text.startswith("-") else text
    if not digits.isdigit():
        raise ValueError(f"{name} must be an integer")
    return int(text)


def _parse_number(text, name):
    text = text.strip()
    if not text:
        raise ValueError(f"{name} is required")
    try:
        if any(char in text for char in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        raise ValueError(f"{name} must be a number") from None


class MacroApp(tk.Tk):
    def __init__(self, runner):
        super().__init__()
        self.runner = runner
        self.log_queue = queue.Queue()
        self._closing = False

        self.title("Ascension Macro")
        self.geometry("960x640")
        self.minsize(960, 640)
        self._steps = []

        self.status_var = tk.StringVar(value="Stopped")
        self.user_id_var = tk.StringVar()
        self.private_server_url_var = tk.StringVar()
        self.place_id_var = tk.StringVar()
        self.check_interval_var = tk.StringVar()
        self.rejoin_interval_var = tk.StringVar()

        self._build()
        self.runner.set_log(self.enqueue_log)
        self.runner.on_stopped = self.notify_stopped
        self._load_settings()
        try:
            self.runner.register_hotkeys(self.request_quit)
        except Exception as exc:
            self._append_log(f"Error: could not register hotkeys: {exc}")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.after(100, self._drain_log)

    def _build(self):
        bar = ttk.Frame(self, padding=(12, 12, 12, 0))
        bar.pack(fill="x")
        ttk.Label(bar, text="Status:").pack(side="left")
        ttk.Label(bar, textvariable=self.status_var).pack(side="left", padx=(4, 12))
        self.stop_button = ttk.Button(bar, text="Stop", command=self.on_stop)
        self.stop_button.pack(side="right")
        self.start_button = ttk.Button(bar, text="Start", command=self.on_start)
        self.start_button.pack(side="right", padx=(0, 8))
        self._set_running(False)

        notebook = ttk.Notebook(self, padding=12)
        notebook.pack(fill="both", expand=True)
        self.notebook = notebook

        settings = ttk.Frame(notebook, padding=12)
        sequence = ttk.Frame(notebook, padding=12)
        self.log_tab = ttk.Frame(notebook, padding=12)
        notebook.add(settings, text="Settings")
        notebook.add(sequence, text="Join sequence")
        notebook.add(self.log_tab, text="Log")

        fields = (
            ("User ID", self.user_id_var),
            ("Private server URL", self.private_server_url_var),
            ("Place ID", self.place_id_var),
            ("Check interval (seconds)", self.check_interval_var),
            ("Rejoin interval (seconds)", self.rejoin_interval_var),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(settings, text=label).grid(row=row, column=0, sticky="w", pady=4)
            entry = ttk.Entry(settings, textvariable=variable)
            entry.grid(row=row, column=1, sticky="ew", padx=(12, 0), pady=4)
        settings.columnconfigure(1, weight=1)

        ttk.Button(settings, text="Save", command=self.on_save).grid(
            row=len(fields), column=1, sticky="e", pady=(12, 0)
        )

        ttk.Label(
            sequence,
            text="Coordinates are pixels inside the Roblox window.",
        ).pack(anchor="w")
        body = ttk.Frame(sequence)
        body.pack(fill="both", expand=True, pady=(8, 0))
        scroll = ttk.Scrollbar(body, orient="vertical")
        self.step_list = tk.Listbox(
            body, activestyle="dotbox", yscrollcommand=scroll.set, exportselection=False
        )
        scroll.configure(command=self.step_list.yview)
        self.step_list.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        step_buttons = ttk.Frame(sequence)
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
        ttk.Button(step_buttons, text="Save", command=self.on_save).pack(side="right")

        self.log_text = scrolledtext.ScrolledText(
            self.log_tab, state="disabled", wrap="word"
        )
        self.log_text.pack(fill="both", expand=True)
        ttk.Button(self.log_tab, text="Clear", command=self.on_clear).pack(
            anchor="e", pady=(8, 0)
        )

    def _load_settings(self):
        try:
            data = config.read_config()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._append_log(f"Error: could not load settings: {exc}")
            self._show_log()
            return
        self.user_id_var.set(_display(data["user_id"]))
        self.private_server_url_var.set(_display(data["private_server_url"]))
        self.place_id_var.set(_display(data["place_id"]))
        self.check_interval_var.set(_display(data["check_interval"]))
        self.rejoin_interval_var.set(_display(data["rejoin_interval"]))
        try:
            self._steps = config.parse_join_sequence(data["join_sequence"])
        except (TypeError, ValueError) as exc:
            self._steps = []
            self._append_log(f"Error: {exc}")
            self._show_log()
        self._refresh_steps()

    def _form_data(self):
        return {
            "user_id": _parse_optional_int(self.user_id_var.get(), "user_id"),
            "private_server_url": self.private_server_url_var.get().strip() or None,
            "place_id": _parse_optional_int(self.place_id_var.get(), "place_id"),
            "check_interval": _parse_number(
                self.check_interval_var.get(), "check_interval"
            ),
            "rejoin_interval": _parse_number(
                self.rejoin_interval_var.get(), "rejoin_interval"
            ),
            "join_sequence": [list(step) for step in self._steps],
        }

    def on_save(self):
        try:
            data = self._form_data()
            config.write_config(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._append_log(f"Error: {exc}")
            self._show_log()
            return
        self._append_log("Settings saved.")

    def on_start(self):
        try:
            data = self._form_data()
        except ValueError as exc:
            self._append_log(f"Error: {exc}")
            self._show_log()
            return
        try:
            config.write_config(data)
        except (OSError, KeyError, TypeError) as exc:
            self._append_log(f"Error: could not save settings: {exc}")
            self._show_log()
            return
        self._append_log("Settings saved.")
        try:
            started = self.runner.start(data)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._append_log(f"Error: {exc}")
            self._show_log()
            return
        if started:
            self._set_running(True)
            self._show_log()

    def on_stop(self):
        self.runner.stop()

    def on_clear(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _show_log(self):
        self.notebook.select(self.log_tab)

    def _refresh_steps(self, select=None):
        self.step_list.delete(0, "end")
        for step in self._steps:
            self.step_list.insert("end", _step_text(step))
        if select is None or not self._steps:
            return
        index = max(0, min(select, len(self._steps) - 1))
        self.step_list.selection_set(index)
        self.step_list.activate(index)
        self.step_list.see(index)

    def _selected_step(self):
        selected = self.step_list.curselection()
        if not selected:
            self._append_log("Select a step first.")
            return None
        return selected[0]

    def on_add_step(self):
        dialog = StepDialog(self)
        if dialog.result is None:
            return
        self._steps.append(dialog.result)
        self._refresh_steps(len(self._steps) - 1)

    def on_edit_step(self):
        index = self._selected_step()
        if index is None:
            return
        dialog = StepDialog(self, self._steps[index])
        if dialog.result is None:
            return
        self._steps[index] = dialog.result
        self._refresh_steps(index)

    def on_remove_step(self):
        index = self._selected_step()
        if index is None:
            return
        del self._steps[index]
        self._refresh_steps(min(index, len(self._steps) - 1))

    def on_move_step_up(self):
        self._move_step(-1)

    def on_move_step_down(self):
        self._move_step(1)

    def _move_step(self, offset):
        index = self._selected_step()
        if index is None:
            return
        target = index + offset
        if target < 0 or target >= len(self._steps):
            return
        self._steps[index], self._steps[target] = self._steps[target], self._steps[index]
        self._refresh_steps(target)

    def on_close(self):
        if self.runner.running():
            self.runner.stop()
        self._closing = True
        self.runner.unregister_hotkeys()
        self.destroy()

    def request_quit(self):
        self.log_queue.put(("quit", "Force exiting program..."))

    def notify_stopped(self):
        self.log_queue.put(("status", "Stopped"))

    def enqueue_log(self, message):
        self.log_queue.put(("log", message))

    def _set_running(self, running):
        self.status_var.set("Running" if running else "Stopped")
        if running:
            self.start_button.state(["disabled"])
            self.stop_button.state(["!disabled"])
        else:
            self.start_button.state(["!disabled"])
            self.stop_button.state(["disabled"])

    def _append_log(self, message):
        stamp = time_text()
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{stamp} {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _drain_log(self):
        if self._closing:
            return
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "status" and payload == "Stopped":
                    self._set_running(False)
                elif kind == "quit":
                    self._append_log(payload)
                    if self.runner.running():
                        self.runner.stop()
                    self._closing = True
                    self.runner.unregister_hotkeys()
                    self.destroy()
                    return
        except queue.Empty:
            pass
        if not self._closing:
            try:
                self.after(100, self._drain_log)
            except tk.TclError:
                return


def time_text():
    return time.strftime("%H:%M:%S")


_ACTION_LABELS = {
    "wait": "Wait",
    "click": "Click",
    "key": "Key",
    "hotkey": "Hotkey",
}
_ACTIONS_BY_LABEL = {label: kind for kind, label in _ACTION_LABELS.items()}


def _step_text(step):
    kind = step[0]
    if kind == "wait":
        return f"Wait {step[1]}"
    if kind == "click":
        return f"Click {step[1]}, {step[2]}"
    if kind == "key":
        return f"Key {step[1]}"
    if kind == "hotkey":
        return "Hotkey " + "+".join(step[1:])
    return str(step)


class StepDialog(tk.Toplevel):
    def __init__(self, master, step=None):
        super().__init__(master)
        self.title("Edit step" if step else "Add step")
        self.resizable(False, False)
        self.result = None
        self.transient(master)

        kind = step[0] if step else "wait"
        self.action_var = tk.StringVar(value=_ACTION_LABELS[kind])
        self.seconds_var = tk.StringVar(
            value=_display(step[1]) if step and kind == "wait" else ""
        )
        self.x_var = tk.StringVar(
            value=_display(step[1]) if step and kind == "click" else ""
        )
        self.y_var = tk.StringVar(
            value=_display(step[2]) if step and kind == "click" else ""
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
            values=list(_ACTION_LABELS.values()),
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
        kind = _ACTIONS_BY_LABEL[self.action_var.get()]
        if kind == "wait":
            rows = (("Seconds", self.seconds_var),)
        elif kind == "click":
            rows = (("X", self.x_var), ("Y", self.y_var))
        elif kind == "key":
            rows = (("Key", self.key_var),)
        else:
            rows = (("Keys", self.hotkey_var),)
        for row, (label, variable) in enumerate(rows):
            ttk.Label(self.fields, text=label).grid(row=row, column=0, sticky="w", pady=4)
            ttk.Entry(self.fields, textvariable=variable, width=24).grid(
                row=row, column=1, sticky="ew", padx=(12, 0), pady=4
            )
        self.fields.columnconfigure(1, weight=1)

    def _ok(self):
        kind = _ACTIONS_BY_LABEL[self.action_var.get()]
        try:
            if kind == "wait":
                seconds = _parse_number(self.seconds_var.get(), "seconds")
                if seconds < 0:
                    raise ValueError("seconds must be 0 or greater")
                step = ["wait", seconds]
            elif kind == "click":
                x = _parse_optional_int(self.x_var.get(), "x")
                y = _parse_optional_int(self.y_var.get(), "y")
                if x is None or y is None:
                    raise ValueError("x and y are required")
                step = ["click", x, y]
            elif kind == "key":
                step = ["key", self.key_var.get()]
            else:
                keys = [
                    part.strip()
                    for part in self.hotkey_var.get().split("+")
                    if part.strip()
                ]
                step = ["hotkey", *keys]
            self.result = config.parse_join_sequence([step])[0]
        except (TypeError, ValueError) as exc:
            self.error_var.set(str(exc))
            return
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.grab_release()
        self.destroy()
