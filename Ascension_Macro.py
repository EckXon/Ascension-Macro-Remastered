import argparse
import subprocess
import sys
import threading
import time
from urllib.parse import parse_qs, urlparse

import keyboard
import requests

import config
import input_control
import join_sequence
import loop_sequence
from gui import MacroApp


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
        self._log = lambda message: None
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
            self._log("Macro started.")
            self._thread.start()
            return True

    def stop(self):
        with self._lock:
            if not self.running():
                self._log("Macro is not running.")
                return
            self._stop.set()
        self._log("Stopping macro...")

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
            self._log("No macro settings yet. Start the macro before using F1.")
            return
        try:
            self._rejoin()
        except Exception as exc:
            self._log(f"Error: {exc}")

    def debug_presence(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F2.")
            return
        user_id = self._settings["user_id"]
        try:
            presence = self._fetch_presence(user_id)
        except Exception as exc:
            self._log(f"Error: {exc}")
            return
        self._log(f"Checked presence for user {user_id}: {presence}")

    def debug_focus(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F3.")
            return
        hwnd = input_control.find_roblox_window(self._settings["username"])
        if not hwnd:
            self._log("Roblox window was not found.")
            return
        if input_control.focus_window(hwnd):
            self._log("Roblox window focused.")
        else:
            self._log("Could not focus the Roblox window.")

    def debug_rename(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F4.")
            return
        username = self._settings["username"]
        hwnd = input_control.rename_roblox_window(username)
        if not hwnd:
            self._log("Roblox window was not found.")
            return
        self._log(f"Renamed Roblox window to {username}.")

    def debug_join_sequence(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F5.")
            return
        try:
            join_sequence.run(
                self._stop,
                self._log,
                self._settings["join_sequence"],
                self._settings["username"],
            )
        except Exception as exc:
            self._log(f"Error: {exc}")

    def debug_loop_sequence(self):
        if not self._settings:
            self._log("No macro settings yet. Start the macro before using F6.")
            return
        settings = self._settings
        if not settings["loop_sequence"]:
            self._log("Loop sequence is empty.")
            return
        hwnd = input_control.find_roblox_window(settings["username"])
        if not hwnd:
            self._log("Roblox window was not found.")
            return
        if not input_control.focus_window(hwnd):
            self._log("Could not focus the Roblox window.")
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
            self._log(f"Error: {exc}")

    def _fetch_presence(self, user_id):
        url = "https://presence.roblox.com/v1/presence/users"
        headers = {"Content-Type": "application/json"}
        data = {"userIds": [user_id]}

        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        info = response.json()["userPresences"][0]
        if self.debug:
            self._log(f"[DEBUG] Checked presence for user {user_id}: {info}")
        return info["userPresenceType"]

    def _resolve_window_username(self, settings):
        display_name = settings.get("display_name")
        if display_name:
            return display_name
        return self._fetch_username(settings["user_id"])

    def _fetch_username(self, user_id):
        response = requests.get(
            f"https://users.roblox.com/v1/users/{user_id}", timeout=15
        )
        response.raise_for_status()
        name = response.json().get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"No username for user {user_id}")
        return name

    def _rejoin(self):
        settings = self._settings
        private_server_url = settings["private_server_url"]
        place_id = settings["place_id"]
        rejoin_interval = settings["rejoin_interval"]

        if private_server_url:
            query = parse_qs(urlparse(private_server_url).query)
            code = query.get("code", [None])[0]
            if not code:
                raise ValueError(
                    f"No share code in private server URL: {private_server_url}"
                )
            deeplink = f"roblox://navigation/share_links?code={code}&type=Server"
        elif place_id:
            deeplink = f"roblox://experiences/start?placeId={place_id}"
        else:
            raise ValueError("Set PRIVATE_SERVER_URL or PLACE_ID")

        self._log(f"Launching Roblox: {deeplink}")
        started = time.monotonic()
        subprocess.Popen([self._roblox_path, deeplink])
        if settings["join_sequence_enabled"]:
            try:
                join_sequence.run(
                    self._stop,
                    self._log,
                    settings["join_sequence"],
                    settings["username"],
                )
            except Exception as exc:
                self._log(f"Error: {exc}")
        remaining = rejoin_interval - (time.monotonic() - started)
        if remaining > 0 and not self._stop.is_set():
            shown = round(remaining, 1)
            if shown == int(shown):
                shown = int(shown)
            if shown:
                self._log(f"Waiting {shown} seconds before the next check.")
            self._stop.wait(remaining)

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
                                f"User {user_id} is offline. Attempting to rejoin server..."
                            )
                            self._rejoin()
                    except Exception as exc:
                        self._log(f"Error: {exc}")
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
