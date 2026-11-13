import subprocess
import time
from urllib.parse import parse_qs, urlparse

import join_sequence
from gui.log_view import MODE_ERROR


def build_deeplink(private_server_url, place_id):
    if private_server_url:
        query = parse_qs(urlparse(private_server_url).query)
        code = query.get("code", [None])[0]
        if not code:
            raise ValueError(
                f"No share code in private server URL: {private_server_url}"
            )
        return f"roblox://navigation/share_links?code={code}&type=Server"
    if place_id:
        return f"roblox://experiences/start?placeId={place_id}"
    raise ValueError("Set PRIVATE_SERVER_URL or PLACE_ID")


def rejoin(settings, roblox_path, stop_event, log):
    deeplink = build_deeplink(settings["private_server_url"], settings["place_id"])
    log(f"Launching Roblox: {deeplink}")
    started = time.monotonic()
    subprocess.Popen([roblox_path, deeplink])
    if settings["join_sequence_enabled"]:
        try:
            join_sequence.run(
                stop_event,
                log,
                settings["join_sequence"],
                settings["username"],
            )
        except Exception as exc:
            log(f"Error: {exc}", MODE_ERROR)
    remaining = settings["rejoin_interval"] - (time.monotonic() - started)
    if remaining > 0 and not stop_event.is_set():
        shown = round(remaining, 1)
        if shown == int(shown):
            shown = int(shown)
        if shown:
            log(f"Waiting {shown} seconds before the next check.")
        stop_event.wait(remaining)
