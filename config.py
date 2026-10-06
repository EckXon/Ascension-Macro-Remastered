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

CONFIG_KEYS = (
    "user_id",
    "private_server_url",
    "place_id",
    "check_interval",
    "rejoin_interval",
)


def _ensure_config_file():
    if os.path.isfile(CONFIG_PATH):
        return
    if not os.path.isfile(EXAMPLE_CONFIG_PATH):
        raise FileNotFoundError(
            f"Missing {EXAMPLE_CONFIG_PATH}. Cannot create {CONFIG_PATH}."
        )
    shutil.copyfile(EXAMPLE_CONFIG_PATH, CONFIG_PATH)


def _read_raw():
    _ensure_config_file()
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {CONFIG_PATH}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{CONFIG_PATH} must contain a JSON object")

    missing = [key for key in CONFIG_KEYS if key not in data]
    if missing:
        raise KeyError(f"Missing keys in {CONFIG_PATH}: {', '.join(missing)}")
    return data


def read_config():
    data = _read_raw()
    return {key: data[key] for key in CONFIG_KEYS}


def write_config(data):
    if not isinstance(data, dict):
        raise TypeError("config data must be a dict")
    missing = [key for key in CONFIG_KEYS if key not in data]
    if missing:
        raise KeyError(f"Missing keys to write: {', '.join(missing)}")
    payload = {key: data[key] for key in CONFIG_KEYS}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")


def _as_int(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} in {CONFIG_PATH} must be an integer")
    return value


def _as_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} in {CONFIG_PATH} must be a number")
    return value


def settings_for_run(data):
    if not isinstance(data, dict):
        raise TypeError("config data must be a dict")

    user_id = data.get("user_id")
    if user_id is None:
        raise ValueError("user_id is required")
    user_id = _as_int(user_id, "user_id")

    private_server_url = data.get("private_server_url")
    if private_server_url is not None and not isinstance(private_server_url, str):
        raise TypeError(
            f"private_server_url in {CONFIG_PATH} must be a string or null"
        )
    if isinstance(private_server_url, str):
        private_server_url = private_server_url.strip() or None

    place_id = data.get("place_id")
    if place_id is not None:
        place_id = _as_int(place_id, "place_id")

    if not private_server_url and not place_id:
        raise ValueError("Set PRIVATE_SERVER_URL or PLACE_ID")

    check_interval = _as_number(data.get("check_interval"), "check_interval")
    rejoin_interval = _as_number(data.get("rejoin_interval"), "rejoin_interval")
    if check_interval <= 0 or rejoin_interval <= 0:
        raise ValueError("check_interval and rejoin_interval must be greater than 0")

    return {
        "user_id": user_id,
        "private_server_url": private_server_url,
        "place_id": place_id,
        "check_interval": check_interval,
        "rejoin_interval": rejoin_interval,
    }


def load_config():
    settings = settings_for_run(read_config())
    return (
        settings["user_id"],
        settings["private_server_url"],
        settings["place_id"],
        settings["check_interval"],
        settings["rejoin_interval"],
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
