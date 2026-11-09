import input_control
import input_sequence

PRESENCE_IN_GAME = 2


def run(stop_event, log, steps, username, presence):
    if not steps or presence != PRESENCE_IN_GAME:
        return
    hwnd = input_control.find_roblox_window(username)
    if not hwnd or not input_control.is_roblox_foreground(hwnd):
        return
    if stop_event.is_set():
        return
    log("Running loop sequence.")
    input_sequence.run_steps(
        hwnd,
        steps,
        stop_event,
        log=log,
        log_prefix="Loop sequence step",
    )
