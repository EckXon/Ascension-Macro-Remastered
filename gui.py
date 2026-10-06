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
        self.geometry("640x420")
        self.minsize(520, 360)

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
        log_tab = ttk.Frame(notebook, padding=12)
        notebook.add(settings, text="Settings")
        notebook.add(log_tab, text="Log")

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

        self.log_text = scrolledtext.ScrolledText(log_tab, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True)
        ttk.Button(log_tab, text="Clear", command=self.on_clear).pack(
            anchor="e", pady=(8, 0)
        )

    def _load_settings(self):
        try:
            data = config.read_config()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._append_log(f"Error: could not load settings: {exc}")
            self.notebook.select(1)
            return
        self.user_id_var.set(_display(data["user_id"]))
        self.private_server_url_var.set(_display(data["private_server_url"]))
        self.place_id_var.set(_display(data["place_id"]))
        self.check_interval_var.set(_display(data["check_interval"]))
        self.rejoin_interval_var.set(_display(data["rejoin_interval"]))

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
        }

    def on_save(self):
        try:
            data = self._form_data()
            config.write_config(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._append_log(f"Error: {exc}")
            self.notebook.select(1)
            return
        self._append_log("Settings saved.")

    def on_start(self):
        try:
            data = self._form_data()
        except ValueError as exc:
            self._append_log(f"Error: {exc}")
            self.notebook.select(1)
            return
        try:
            config.write_config(data)
        except (OSError, KeyError, TypeError) as exc:
            self._append_log(f"Error: could not save settings: {exc}")
            self.notebook.select(1)
            return
        self._append_log("Settings saved.")
        try:
            started = self.runner.start(data)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._append_log(f"Error: {exc}")
            self.notebook.select(1)
            return
        if started:
            self._set_running(True)
            self.notebook.select(1)

    def on_stop(self):
        self.runner.stop()

    def on_clear(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

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
