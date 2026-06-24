import time
import requests
import webbrowser
import keyboard
import argparse
import sys

#-CONFIGURATION-#
USER_ID = 4348247182  # target Roblox user ID
PRIVATE_SERVER_URL = "https://www.roblox.com/share?code=029858a0f353be4f91e4e373b47da33b&type=Server"
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

def rejoin_server():
    print("Opening private server link...")
    webbrowser.open(PRIVATE_SERVER_URL)
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