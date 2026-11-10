import input_control


def run_step(hwnd, step, stop_event):
    if not step:
        raise ValueError(f"invalid step: {step!r}")
    kind = step[0]
    if kind == "wait":
        if len(step) != 2:
            raise ValueError(f"invalid step: {step!r}")
        input_control.wait(step[1], stop_event)
    elif kind == "click":
        if len(step) not in (3, 4):
            raise ValueError(f"invalid step: {step!r}")
        duration = step[3] if len(step) == 4 else 0.5
        input_control.client_click(hwnd, step[1], step[2], duration)
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


def run_steps(hwnd, steps, stop_event, log=None, log_prefix="Step"):
    for step in steps:
        if stop_event.is_set():
            return False
        try:
            run_step(hwnd, step, stop_event)
        except Exception as exc:
            if log is not None:
                log(f"{log_prefix} failed: {step}: {exc}")
            return False
    return True
