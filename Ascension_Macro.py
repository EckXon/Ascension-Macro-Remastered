import json
import os
import shutil
import subprocess
import time
import winreg
from urllib.parse import parse_qs, urlparse

import requests
import keyboard
import argparse
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
EXAMPLE_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.example.json")

def load_config():
    if not os.path.isfile(CONFIG_PATH):
        if not os.path.isfile(EXAMPLE_CONFIG_PATH):
            raise FileNotFoundError(
                f"Missing {EXAMPLE_CONFIG_PATH}. Cannot create {CONFIG_PATH}."
            )
        shutil.copyfile(EXAMPLE_CONFIG_PATH, CONFIG_PATH)

    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {CONFIG_PATH}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{CONFIG_PATH} must contain a JSON object")

    required = (
        "user_id",
        "private_server_url",
        "place_id",
        "check_interval",
        "rejoin_interval",
    )
    missing = [key for key in required if key not in data]
    if missing:
        raise KeyError(f"Missing keys in {CONFIG_PATH}: {', '.join(missing)}")

    def as_int(value, name):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} in {CONFIG_PATH} must be an integer")
        return value

    def as_number(value, name):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{name} in {CONFIG_PATH} must be a number")
        return value

    private_server_url = data["private_server_url"]
    if private_server_url is not None and not isinstance(private_server_url, str):
        raise TypeError(
            f"private_server_url in {CONFIG_PATH} must be a string or null"
        )

    return (
        as_int(data["user_id"], "user_id"),
        private_server_url,
        as_int(data["place_id"], "place_id"),
        as_number(data["check_interval"], "check_interval"),
        as_number(data["rejoin_interval"], "rejoin_interval"),
    )

USER_ID, PRIVATE_SERVER_URL, PLACE_ID, CHECK_INTERVAL, REJOIN_INTERVAL = load_config()

running = True
alive = True

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

args = parse_args()

if args.debug:
    print("Debug mode enabled")

def debug_print(message):
    if args.debug:
        print(f"[DEBUG] {message}")

def get_presence(user_id: int):
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {"Content-Type": "application/json"}
    data = {"userIds": [user_id]}

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    info = response.json()["userPresences"][0]
    debug_print(f"Checked presence for user {user_id}: {info}")

    return info["userPresenceType"]

def find_roblox_player() -> str:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Classes\roblox\shell\open\command",
        ) as key:
            command, _ = winreg.QueryValueEx(key, "")
        if command.startswith('"'):
            exe = command.split('"')[1]
        else:
            exe = command.split()[0]
        if os.path.isfile(exe) and os.path.basename(exe).lower() == "robloxplayerbeta.exe":
            return exe
    except OSError:
        pass

    local_app_data = os.environ.get("LOCALAPPDATA")
    versions = os.path.join(local_app_data or "", "Roblox", "Versions")
    candidates = []
    if os.path.isdir(versions):
        for name in os.listdir(versions):
            exe = os.path.join(versions, name, "RobloxPlayerBeta.exe")
            if os.path.isfile(exe):
                candidates.append(exe)
    if not candidates:
        raise FileNotFoundError("RobloxPlayerBeta.exe not found")
    return max(candidates, key=os.path.getmtime)

def rejoin_server():
    if PRIVATE_SERVER_URL:
        query = parse_qs(urlparse(PRIVATE_SERVER_URL).query)
        code = query.get("code", [None])[0]
        if not code:
            raise ValueError(f"No share code in private server URL: {PRIVATE_SERVER_URL}")
        deeplink = f"roblox://navigation/share_links?code={code}&type=Server"
    elif PLACE_ID:
        deeplink = f"roblox://experiences/start?placeId={PLACE_ID}"
    else:
        raise ValueError("Set PRIVATE_SERVER_URL or PLACE_ID")

    exe = find_roblox_player()
    print(f"Launching Roblox player: {exe}")
    subprocess.Popen([exe, deeplink])
    time.sleep(REJOIN_INTERVAL)

def main():
    while alive:
        if running:
            presence = get_presence(USER_ID)
            if presence != 2:  # User is offline
                print(f"User {USER_ID} is offline. Attempting to rejoin server...")
                rejoin_server()
        time.sleep(CHECK_INTERVAL)
    print("Main loop exited.")

def exit_program():
    global alive
    alive = False
    print("Exiting program...")

def force_exit():
    global alive
    alive = False
    print("Force exiting program...")
    sys.exit(0)

if args.debug:
    print("Setting up debug hotkeys...")
    keyboard.add_hotkey('F1', rejoin_server)
    keyboard.add_hotkey('F2', get_presence, args=(USER_ID,))

keyboard.add_hotkey('F8', exit_program)
keyboard.add_hotkey('F9', force_exit)

if __name__ == "__main__":
    main()