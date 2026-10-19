import time

import input_control

WINDOW_TIMEOUT = 60
POLL_INTERVAL = 0.5


def run(stop_event, log, steps, username):
    log("Waiting for the Roblox window.")
    hwnd = _wait_for_window(stop_event, username)
    if stop_event.is_set():
        return
    if hwnd is None:
        log("Roblox window was not found. Skipping on-join steps.")
        return
    if not input_control.focus_window(hwnd):
        log("Could not focus the Roblox window.")
    else:
        log("Roblox window focused.")
    for step in steps:
        if stop_event.is_set():
            return
        try:
            _run_step(hwnd, step, stop_event)
        except Exception as exc:
            log(f"On-join step failed: {step}: {exc}")
            return


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


def _run_step(hwnd, step, stop_event):
    if not step:
        raise ValueError(f"invalid step: {step!r}")
    kind = step[0]
    if kind == "wait":
        if len(step) != 2:
            raise ValueError(f"invalid step: {step!r}")
        input_control.wait(step[1], stop_event)
    elif kind == "click":
        if len(step) != 3:
            raise ValueError(f"invalid step: {step!r}")
        input_control.client_click(hwnd, step[1], step[2])
    elif kind == "key":
        if len(step) != 2:
            raise ValueError(f"invalid step: {step!r}")
        input_control.press_key(step[1])
    elif kind == "hotkey":
        if len(step) < 2:
            raise ValueError(f"invalid step: {step!r}")
        input_control.hotkey(*step[1:])
    else:
        raise ValueError(f"unknown step: {step!r}")
