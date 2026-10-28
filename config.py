import json
import os
import sys
import winreg


def app_dir():
    """Folder for files the user edits, next to the EXE when frozen."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


SCRIPT_DIR = app_dir()
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
EXAMPLE_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.example.json")

DEFAULT_JOIN_SEQUENCE = []
DEFAULT_LOOP_SEQUENCE = []

CONFIG_KEYS = {
    "user_id": None,
    "display_name": None,
    "private_server_url": None,
    "place_id": None,
    "check_interval": 5,
    "rejoin_interval": 120,
    "loop_sequence_interval": 60,
    "join_sequence": [list(step) for step in DEFAULT_JOIN_SEQUENCE],
    "loop_sequence": [list(step) for step in DEFAULT_LOOP_SEQUENCE],
}


def _ensure_config_file():
    if os.path.isfile(CONFIG_PATH):
        return

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(CONFIG_KEYS, f, indent=2)
        f.write("\n")


def _read_raw():
    _ensure_config_file()
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {CONFIG_PATH}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{CONFIG_PATH} must contain a JSON object")

    if "join_sequence" not in data:
        data["join_sequence"] = [list(step) for step in DEFAULT_JOIN_SEQUENCE]
    if "loop_sequence" not in data:
        data["loop_sequence"] = [list(step) for step in DEFAULT_LOOP_SEQUENCE]
    if "loop_sequence_interval" not in data:
        data["loop_sequence_interval"] = CONFIG_KEYS["loop_sequence_interval"]
    if "display_name" not in data:
        data["display_name"] = CONFIG_KEYS["display_name"]

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


def _as_key(value, name):
    if not isinstance(value, str) or not value.strip():
        raise TypeError(f"{name} in {CONFIG_PATH} must be a non-empty string")
    return value.strip()


def _parse_input_sequence(value, sequence_name):
    if not isinstance(value, list):
        raise TypeError(f"{sequence_name} in {CONFIG_PATH} must be a list")
    steps = []
    for index, step in enumerate(value):
        name = f"{sequence_name}[{index}]"
        if not isinstance(step, (list, tuple)) or not step:
            raise TypeError(f"{name} in {CONFIG_PATH} must be a list")
        kind = step[0]
        if kind == "wait":
            if len(step) != 2:
                raise ValueError(f"{name} in {CONFIG_PATH} must be [wait, seconds]")
            seconds = _as_number(step[1], f"{name} seconds")
            if seconds < 0:
                raise ValueError(f"{name} seconds must be 0 or greater")
            steps.append(("wait", seconds))
        elif kind == "click":
            if len(step) not in (3, 4):
                raise ValueError(
                    f"{name} in {CONFIG_PATH} must be [click, x, y] or "
                    f"[click, x, y, duration]"
                )
            x = _as_int(step[1], f"{name} x")
            y = _as_int(step[2], f"{name} y")
            duration = 0
            if len(step) == 4:
                duration = _as_number(step[3], f"{name} duration")
                if duration < 0:
                    raise ValueError(f"{name} duration must be 0 or greater")
            if duration:
                steps.append(("click", x, y, duration))
            else:
                steps.append(("click", x, y))
        elif kind == "key":
            if len(step) != 2:
                raise ValueError(f"{name} in {CONFIG_PATH} must be [key, name]")
            steps.append(("key", _as_key(step[1], f"{name} key")))
        elif kind == "hotkey":
            if len(step) < 2:
                raise ValueError(f"{name} in {CONFIG_PATH} must include at least one key")
            keys = [
                _as_key(key, f"{name} key {offset}")
                for offset, key in enumerate(step[1:], start=1)
            ]
            steps.append(("hotkey", *keys))
        else:
            raise ValueError(f"{name} in {CONFIG_PATH} has unknown action {kind!r}")
    return steps


def parse_join_sequence(value):
    return _parse_input_sequence(value, "join_sequence")


def parse_loop_sequence(value):
    return _parse_input_sequence(value, "loop_sequence")


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

    display_name = data.get("display_name")
    if display_name is not None and not isinstance(display_name, str):
        raise TypeError(f"display_name in {CONFIG_PATH} must be a string or null")
    if isinstance(display_name, str):
        display_name = display_name.strip() or None

    check_interval = _as_number(data.get("check_interval"), "check_interval")
    rejoin_interval = _as_number(data.get("rejoin_interval"), "rejoin_interval")
    loop_sequence_interval = _as_number(
        data.get("loop_sequence_interval"), "loop_sequence_interval"
    )
    if check_interval <= 0 or rejoin_interval <= 0:
        raise ValueError("check_interval and rejoin_interval must be greater than 0")
    if loop_sequence_interval <= 0:
        raise ValueError("loop_sequence_interval must be greater than 0")

    return {
        "user_id": user_id,
        "display_name": display_name,
        "private_server_url": private_server_url,
        "place_id": place_id,
        "check_interval": check_interval,
        "rejoin_interval": rejoin_interval,
        "loop_sequence_interval": loop_sequence_interval,
        "join_sequence": parse_join_sequence(data.get("join_sequence")),
        "loop_sequence": parse_loop_sequence(data.get("loop_sequence")),
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
