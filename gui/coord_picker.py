import tkinter as tk

import win32api

import input_control


class CoordinatePicker:
    def __init__(self, master, resolve_username):
        self.master = master
        self.resolve_username = resolve_username
        self._active = False
        self._button = None
        self._username = None
        self._tooltip = None
        self._tooltip_label = None
        self._after_id = None

    def toggle(self, button):
        if self._active:
            self.stop()
        else:
            self.start(button)

    def start(self, button):
        self._username = self.resolve_username()
        self._active = True
        self._button = button
        button.configure(text="Hide coordinates")
        self._update()

    def stop(self):
        self._active = False
        if self._button is not None:
            self._button.configure(text="Show coordinates")
            self._button = None
        if self._after_id is not None:
            self.master.after_cancel(self._after_id)
            self._after_id = None
        self._destroy_tooltip()

    def _destroy_tooltip(self):
        if self._tooltip is not None:
            self._tooltip.destroy()
            self._tooltip = None
            self._tooltip_label = None

    def _show_tooltip(self, text, x, y):
        if self._tooltip is None:
            tooltip = tk.Toplevel(self.master)
            tooltip.wm_overrideredirect(True)
            tooltip.attributes("-topmost", True)
            frame = tk.Frame(
                tooltip,
                background="#ffffe0",
                highlightbackground="#000000",
                highlightthickness=1,
            )
            frame.pack()
            self._tooltip_label = tk.Label(
                frame,
                text=text,
                background="#ffffe0",
                padx=6,
                pady=4,
            )
            self._tooltip_label.pack()
            self._tooltip = tooltip
        else:
            self._tooltip_label.configure(text=text)
        self._tooltip.wm_geometry(f"+{x}+{y}")

    def _update(self):
        if not self._active or getattr(self.master, "_closing", False):
            return
        try:
            position = input_control.cursor_client_position(username=self._username)
        except Exception:
            position = None
        if position is None:
            text = "Roblox window not found"
        else:
            x, y = position
            text = f"X: {x}, Y: {y}"
        screen_x, screen_y = win32api.GetCursorPos()
        self._show_tooltip(text, screen_x + 16, screen_y + 16)
        self._after_id = self.master.after(50, self._update)
