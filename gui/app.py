import queue
import tkinter as tk
from tkinter import ttk

import config
import input_control
from gui.coord_picker import CoordinatePicker
from gui.fields import parse_optional_int
from gui.log_view import MODE_ERROR, MODE_SYSTEM, MODE_USER, LogView
from gui.sequence_editor import SequenceEditor
from gui.settings_form import SettingsForm

TAB_WIDTH = 14
GUI_MIN_WIDTH = 1080
GUI_MIN_HEIGHT = 720

class MacroApp(tk.Tk):
    def __init__(self, runner):
        super().__init__()
        self.runner = runner
        self.log_queue = queue.Queue()
        self._closing = False

        self.title("Ascension Macro")
        self.geometry(f"{GUI_MIN_WIDTH}x{GUI_MIN_HEIGHT}")
        self.minsize(GUI_MIN_WIDTH, GUI_MIN_HEIGHT)
        self.status_var = tk.StringVar(value="Stopped")

        self._build()
        self.runner.set_log(self.enqueue_log)
        self.runner.on_stopped = self.notify_stopped
        self._load_settings()
        try:
            self.runner.register_hotkeys(self.request_quit)
        except Exception as exc:
            self._append_log(f"Error: could not register hotkeys: {exc}", MODE_ERROR)

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

        def tab_width(text):
            return str.center(text, TAB_WIDTH)

        settings = ttk.Frame(notebook, padding=12)
        join_tab = ttk.Frame(notebook, padding=12)
        loop_tab = ttk.Frame(notebook, padding=12)
        self.log_tab = ttk.Frame(notebook, padding=12)
        notebook.add(settings, text=tab_width("Settings"))
        notebook.add(join_tab, text=tab_width("Join sequence"))
        notebook.add(loop_tab, text=tab_width("Loop sequence"))
        notebook.add(self.log_tab, text=tab_width("Log"))

        self.settings = SettingsForm(settings, on_save=self.on_save)
        self.picker = CoordinatePicker(self, self._resolve_roblox_username)
        self.join_editor = SequenceEditor(
            join_tab,
            on_save=self.on_save,
            on_log=self._append_log,
            on_toggle_coords=self.picker.toggle,
            parse_step=config.parse_join_sequence,
            description="Runs once after each rejoin (join sequence and rejoin interval).",
        )
        self.loop_editor = SequenceEditor(
            loop_tab,
            on_save=self.on_save,
            on_log=self._append_log,
            on_toggle_coords=self.picker.toggle,
            parse_step=config.parse_loop_sequence,
            description=(
                "Runs on loop sequence interval while in-game, rejoin is finished, "
                "and Roblox is the active window."
            ),
        )
        self.log_view = LogView(self.log_tab)

    def _load_settings(self):
        try:
            data = config.read_config()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._append_log(f"Error: could not load settings: {exc}", MODE_ERROR)
            self._show_log()
            return
        self.settings.load(data)
        if not self.settings.display_name():
            try:
                self._fill_display_name_if_empty()
            except (OSError, ValueError) as exc:
                self._append_log(f"Error: could not resolve display name: {exc}", MODE_ERROR)
        try:
            self.join_editor.set_steps(config.parse_join_sequence(data["join_sequence"]))
        except (TypeError, ValueError) as exc:
            self.join_editor.set_steps([])
            self._append_log(f"Error: {exc}", MODE_ERROR)
            self._show_log()
        try:
            self.loop_editor.set_steps(config.parse_loop_sequence(data["loop_sequence"]))
        except (TypeError, ValueError) as exc:
            self.loop_editor.set_steps([])
            self._append_log(f"Error: {exc}", MODE_ERROR)
            self._show_log()

    def _fill_display_name_if_empty(self):
        if self.settings.display_name():
            return self.settings.display_name()
        user_id = parse_optional_int(self.settings.user_id_text(), "user_id")
        if user_id is None:
            return None
        name = self.runner._fetch_username(user_id)
        self.settings.set_display_name(name)
        return name

    def _form_data(self):
        data = self.settings.read()
        data["join_sequence"] = [list(step) for step in self.join_editor.steps]
        data["loop_sequence"] = [list(step) for step in self.loop_editor.steps]
        return data

    def on_save(self):
        try:
            self._fill_display_name_if_empty()
            data = self._form_data()
            config.write_config(data)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self._append_log(f"Error: {exc}", MODE_ERROR)
            self._show_log()
            return
        self._append_log("Settings saved.", MODE_USER)

    def on_start(self):
        try:
            self._fill_display_name_if_empty()
            data = self._form_data()
        except (OSError, ValueError) as exc:
            self._append_log(f"Error: {exc}", MODE_ERROR)
            self._show_log()
            return
        try:
            config.write_config(data)
        except (OSError, KeyError, TypeError) as exc:
            self._append_log(f"Error: could not save settings: {exc}", MODE_ERROR)
            self._show_log()
            return
        self._append_log("Settings saved.", MODE_USER)
        try:
            started = self.runner.start(data)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            self._append_log(f"Error: {exc}", MODE_ERROR)
            self._show_log()
            return
        if started:
            self._set_running(True)
            self._show_log()

    def on_stop(self):
        self.runner.stop()

    def _show_log(self):
        self.notebook.select(self.log_tab)

    def _resolve_roblox_username(self):
        display_name = self.settings.display_name()
        if display_name:
            return display_name
        settings = getattr(self.runner, "_settings", None)
        if settings and settings.get("username"):
            return settings["username"]
        try:
            filled = self._fill_display_name_if_empty()
            if filled:
                return filled
        except (OSError, ValueError):
            pass
        return input_control.ROBLOX_TITLE

    def on_close(self):
        self.picker.stop()
        if self.runner.running():
            self.runner.stop()
        self._closing = True
        self.runner.unregister_hotkeys()
        self.destroy()

    def request_quit(self):
        self.log_queue.put(("quit", "Force exiting program..."))

    def notify_stopped(self):
        self.log_queue.put(("status", "Stopped"))

    def enqueue_log(self, message, mode=MODE_SYSTEM):
        self.log_queue.put(("log", (message, mode)))

    def _set_running(self, running):
        self.status_var.set("Running" if running else "Stopped")
        if running:
            self.start_button.state(["disabled"])
            self.stop_button.state(["!disabled"])
        else:
            self.start_button.state(["!disabled"])
            self.stop_button.state(["disabled"])

    def _append_log(self, message, mode=MODE_SYSTEM):
        self.log_view.append(message, mode)

    def _drain_log(self):
        if self._closing:
            return
        try:
            while True:
                kind, payload = self.log_queue.get_nowait()
                if kind == "log":
                    message, mode = payload
                    self._append_log(message, mode)
                elif kind == "status" and payload == "Stopped":
                    self._set_running(False)
                elif kind == "quit":
                    self._append_log(payload, MODE_USER)
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
