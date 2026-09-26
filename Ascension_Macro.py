import os
import subprocess
import time
import winreg
from urllib.parse import parse_qs, urlparse

import requests
import keyboard
import argparse
import sys

#-CONFIGURATION-#
USER_ID = 4348247182  # target Roblox user ID
PRIVATE_SERVER_URL = None # private server URL from roblox.com/games/PLACE_ID/... ;
PLACE_ID = 110806816173057  # place ID from roblox.com/games/PLACE_ID/... ; used when PRIVATE_SERVER_URL is empty
CHECK_INTERVAL = 5  # seconds
REJOIN_INTERVAL = 120  # seconds
#---------------#

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