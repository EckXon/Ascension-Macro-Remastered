def display(value):
    if value is None:
        return ""
    return str(value)


def parse_optional_int(text, name):
    text = text.strip()
    if not text:
        return None
    digits = text[1:] if text.startswith("-") else text
    if not digits.isdigit():
        raise ValueError(f"{name} must be an integer")
    return int(text)


def parse_number(text, name):
    text = text.strip()
    if not text:
        raise ValueError(f"{name} is required")
    try:
        if any(char in text for char in ".eE"):
            return float(text)
        return int(text)
    except ValueError:
        raise ValueError(f"{name} must be a number") from None


def step_text(step):
    kind = step[0]
    if kind == "wait":
        return f"Wait {step[1]}"
    if kind == "click":
        text = f"Click {step[1]}, {step[2]}"
        if len(step) > 3:
            text += f" ({step[3]}s)"
        return text
    if kind == "key":
        return f"Key {step[1]}"
    if kind == "hotkey":
        return "Hotkey " + "+".join(step[1:])
    return str(step)


ACTION_LABELS = {
    "wait": "Wait",
    "click": "Click",
    "key": "Key",
    "hotkey": "Hotkey",
}
ACTIONS_BY_LABEL = {label: kind for kind, label in ACTION_LABELS.items()}
