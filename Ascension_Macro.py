import subprocess
import time
from urllib.parse import parse_qs, urlparse

import requests
import keyboard
import argparse
import sys

import config

def _frozen_excepthook(exc_type, exc, tb):
    import traceback

    traceback.print_exception(exc_type, exc, tb)
    if getattr(sys, "frozen", False) and not issubclass(exc_type, KeyboardInterrupt):
        try:
            input("Press Enter to close...")
        except EOFError:
            pass


sys.excepthook = _frozen_excepthook

USER_ID, PRIVATE_SERVER_URL, PLACE_ID, CHECK_INTERVAL, REJOIN_INTERVAL = config.load_config()
ROBLOX_PLAYER_PATH = config.find_roblox_player()

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

    subprocess.Popen([ROBLOX_PLAYER_PATH, deeplink])
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