import argparse
import sys
import threading
import time

import keyboard

import config
import input_control
import join_sequence
import loop_sequence
import rejoin
import roblox_api
from gui import MacroApp
from gui.log_view import MODE_ERROR, MODE_SYSTEM, MODE_USER, MODE_WARN


def _frozen_excepthook(exc_type, exc, tb):
    import traceback

    traceback.print_exception(exc_type, exc, tb)
    if getattr(sys, "frozen", False) and not issubclass(exc_type, KeyboardInterrupt):
        try:
            input("Press Enter to close...")
        except EOFError:
            pass


sys.excepthook = _frozen_excepthook


class MacroRunner:
    def __init__(self, debug=False):
        self.debug = debug
        self.on_stopped = None
        self._log = lambda message, mode=MODE_SYSTEM: None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        self._settings = None
        self._roblox_path = None
        self._hotkeys = []

    def set_log(self, callback):
        self._log = callback

    def running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self, data):
        with self._lock:
            if self.running():
                return False
        settings = config.settings_for_run(data)
        settings["username"] = self._resolve_window_username(settings)
        roblox_path = config.find_roblox_player()
        with self._lock:
            if self.running():
                return False
            self._settings = settings
            self._roblox_path = roblox_path
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._loop, name="macro", daemon=True
            )
            self._log("Macro started.", MODE_USER)
            self._thread.start()
            return True

    def stop(self):
        with self._lock:
            if not self.running():
                self._log("Macro is not running.", MODE_WARN)
                return
            self._stop.set()
        self._log("Stopping macro...", MODE_USER)

    def register_hotkeys(self, on_force_exit):
        self.unregister_hotkeys()
        if self.debug:
            self._log("Debug mode enabled")
            self._log("Setting up debug hotkeys...")
            self._log(
                "F1 rejoin, F2 presence, F3 focus window, F4 rename window, "
                "F5 join sequence, F6 loop sequence"
            )
            self._hotkeys.append(keyboard.add_hotkey("F1", self.debug_rejoin))
            self._hotkeys.append(keyboard.add_hotkey("F2", self.debug_presence))
            self._hotkeys.append(keyboard.add_hotkey("F3", self.debug_focus))
            self._hotkeys.append(keyboard.add_hotkey("F4", self.debug_rename))
            self._hotkeys.append(keyboard.add_hotkey("F5", self.debug_join_sequence))
            self._hotkeys.append(keyboard.add_hotkey("F6", self.debug_loop_sequence))
        self._hotkeys.append(keyboard.add_hotkey("F8", self.stop))
        self._hotkeys.append(keyboard.add_hotkey("F9", on_force_exit))

    def unregister_hotkeys(self):
        while self._hotkeys:
            hotkey = self._hotkeys.pop()
            try:
                keyboard.remove_hotkey(hotkey)
            except (KeyError, ValueError):
                pass

    def debug_rejoin(self):
        if not self._settings or not self._roblox_path:
            self._log("No macro settings yet. Start the macro before using F1.", MODE_WARN)
            return
        try:
            self._rejoin()
        except Exception as exc:
            self._log(f"Error: {exc}", MODE_ERROR)

    def debug_presence(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F2.", MODE_WARN)
            return
        user_id = self._settings["user_id"]
        try:
            presence = self._fetch_presence(user_id)
        except Exception as exc:
            self._log(f"Error: {exc}", MODE_ERROR)
            return
        self._log(f"Checked presence for user {user_id}: {presence}", MODE_USER)

    def debug_focus(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F3.", MODE_WARN)
            return
        hwnd = input_control.find_roblox_window(self._settings["username"])
        if not hwnd:
            self._log("Roblox window was not found.", MODE_WARN)
            return
        if input_control.focus_window(hwnd):
            self._log("Roblox window focused.", MODE_USER)
        else:
            self._log("Could not focus the Roblox window.", MODE_WARN)

    def debug_rename(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F4.", MODE_WARN)
            return
        username = self._settings["username"]
        hwnd = input_control.rename_roblox_window(username)
        if not hwnd:
            self._log("Roblox window was not found.", MODE_WARN)
            return
        self._log(f"Renamed Roblox window to {username}.", MODE_USER)

    def debug_join_sequence(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F5.", MODE_WARN)
            return
        try:
            join_sequence.run(
                self._stop,
                self._log,
                self._settings["join_sequence"],
                self._settings["username"],
            )
        except Exception as exc:
            self._log(f"Error: {exc}", MODE_ERROR)

    def debug_loop_sequence(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F6.", MODE_WARN)
            return
        settings = self._settings
        if not settings["loop_sequence"]:
            self._log("Loop sequence is empty.", MODE_WARN)
            return
        hwnd = input_control.find_roblox_window(settings["username"])
        if not hwnd:
            self._log("Roblox window was not found.", MODE_WARN)
            return
        if not input_control.focus_window(hwnd):
            self._log("Could not focus the Roblox window.", MODE_WARN)
            return
        try:
            loop_sequence.run(
                self._stop,
                self._log,
                settings["loop_sequence"],
                settings["username"],
                loop_sequence.PRESENCE_IN_GAME,
            )
        except Exception as exc:
            self._log(f"Error: {exc}", MODE_ERROR)

    def _fetch_presence(self, user_id):
        return roblox_api.fetch_presence(user_id, self._log, debug=self.debug)

    def _resolve_window_username(self, settings):
        display_name = settings.get("display_name")
        if display_name:
            return display_name
        return self._fetch_username(settings["user_id"])

    def _fetch_username(self, user_id):
        return roblox_api.fetch_username(user_id)

    def _rejoin(self):
        rejoin.rejoin(self._settings, self._roblox_path, self._stop, self._log)

    def _loop(self):
        try:
            presence = None
            now = time.monotonic()
            next_presence = now
            loop_enabled = self._settings["loop_sequence_enabled"]
            next_loop_sequence = (
                now + self._settings["loop_sequence_interval"] if loop_enabled else None
            )
            while not self._stop.is_set():
                settings = self._settings
                now = time.monotonic()
                if now >= next_presence:
                    user_id = settings["user_id"]
                    try:
                        presence = self._fetch_presence(user_id)
                        self._log(f"Checked presence for user {user_id}: {presence}")
                        if presence != 2:
                            self._log(
                                f"User {user_id} is offline. Attempting to rejoin server...",
                                MODE_WARN,
                            )
                            self._rejoin()
                    except Exception as exc:
                        self._log(f"Error: {exc}", MODE_ERROR)
                    next_presence = time.monotonic() + settings["check_interval"]
                if next_loop_sequence is not None:
                    now = time.monotonic()
                    if now >= next_loop_sequence:
                        loop_sequence.run(
                            self._stop,
                            self._log,
                            settings["loop_sequence"],
                            settings["username"],
                            presence,
                        )
                        next_loop_sequence = (
                            time.monotonic() + settings["loop_sequence_interval"]
                        )
                if self._stop.is_set():
                    break
                now = time.monotonic()
                delay_until = next_presence
                if next_loop_sequence is not None:
                    delay_until = min(delay_until, next_loop_sequence)
                delay = delay_until - now
                if delay > 0:
                    self._stop.wait(delay)
        finally:
            self._log("Macro stopped.")
            if self.on_stopped is not None:
                self.on_stopped()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


def main():
    args = parse_args()
    runner = MacroRunner(debug=args.debug)
    app = MacroApp(runner)
    app.mainloop()


if __name__ == "__main__":
    main()
