import argparse
import subprocess
import sys
import threading
from urllib.parse import parse_qs, urlparse

import keyboard
import requests

import config
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
            self._hotkeys.append(keyboard.add_hotkey("F1", self.debug_rejoin))
            self._hotkeys.append(keyboard.add_hotkey("F2", self.debug_presence))
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
        subprocess.Popen([self._roblox_path, deeplink])
        self._log(f"Waiting {rejoin_interval} seconds before the next check.")
        self._stop.wait(rejoin_interval)

    def _loop(self):
        try:
            while not self._stop.is_set():
                settings = self._settings
                user_id = settings["user_id"]
                check_interval = settings["check_interval"]
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
                self._stop.wait(check_interval)
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
