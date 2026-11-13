import requests


def fetch_presence(user_id, log, debug=False):
    url = "https://presence.roblox.com/v1/presence/users"
    headers = {"Content-Type": "application/json"}
    data = {"userIds": [user_id]}

    response = requests.post(url, json=data, headers=headers)
    response.raise_for_status()
    info = response.json()["userPresences"][0]
    if debug:
        log(f"[DEBUG] Checked presence for user {user_id}: {info}")
    return info["userPresenceType"]


def fetch_username(user_id):
    response = requests.get(
        f"https://users.roblox.com/v1/users/{user_id}", timeout=15
    )
    response.raise_for_status()
    name = response.json().get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"No username for user {user_id}")
    return name
