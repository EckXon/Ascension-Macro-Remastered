import json
import os
import shutil
import sys
import winreg


def app_dir():
    """Folder for files the user edits, next to the EXE when frozen."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def bundle_dir():
    """Folder that contains bundled read-only data such as the example config."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", app_dir())
    return os.path.dirname(os.path.abspath(__file__))


SCRIPT_DIR = app_dir()
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
EXAMPLE_CONFIG_PATH = os.path.join(bundle_dir(), "config.example.json")


def load_config():
    if not os.path.isfile(CONFIG_PATH):
        if not os.path.isfile(EXAMPLE_CONFIG_PATH):
            raise FileNotFoundError(
                f"Missing {EXAMPLE_CONFIG_PATH}. Cannot create {CONFIG_PATH}."
            )
        #shutil.copyfile(EXAMPLE_CONFIG_PATH, CONFIG_PATH)

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
