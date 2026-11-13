import time

import input_control
import input_sequence
from gui.log_view import MODE_WARN

WINDOW_TIMEOUT = 60
POLL_INTERVAL = 0.5


def run(stop_event, log, steps, username):
    log("Waiting for the Roblox window.")
    hwnd = _wait_for_window(stop_event, username)
    if stop_event.is_set():
        return
    if hwnd is None:
        log("Roblox window was not found. Skipping on-join steps.", MODE_WARN)
        return
    if not input_control.focus_window(hwnd):
        log("Could not focus the Roblox window.", MODE_WARN)
    else:
        log("Roblox window focused.")
    input_sequence.run_steps(
        hwnd,
        steps,
        stop_event,
        log=log,
        log_prefix="On-join step",
    )


def _wait_for_window(stop_event, username):
    deadline = time.monotonic() + WINDOW_TIMEOUT
    while not stop_event.is_set():
        hwnd = input_control.find_roblox_window(username)
        if hwnd:
            return hwnd
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        stop_event.wait(min(POLL_INTERVAL, remaining))
    return None
