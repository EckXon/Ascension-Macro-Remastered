import input_control
import input_sequence

PRESENCE_IN_GAME = 2


def run(
    stop_event,
    log,
    settings_getter,
    presence_getter,
    rejoin_in_progress,
    run_lock,
):
    while not stop_event.is_set():
        settings = settings_getter()
        if settings is None:
            stop_event.wait(1)
            continue
        interval = settings["loop_sequence_interval"]
        steps = settings["loop_sequence"]
        username = settings["username"]

        if stop_event.wait(interval):
            break

        if not steps:
            continue
        if rejoin_in_progress():
            continue
        if presence_getter() != PRESENCE_IN_GAME:
            continue

        hwnd = input_control.find_roblox_window(username)
        if not hwnd or not input_control.is_roblox_foreground(hwnd):
            continue

        if not run_lock.acquire(blocking=False):
            continue
        try:
            if stop_event.is_set():
                continue
            log("Running loop sequence.")
            input_sequence.run_steps(
                hwnd,
                steps,
                stop_event,
                log=log,
                log_prefix="Loop sequence step",
            )
        finally:
            run_lock.release()
