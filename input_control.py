import os
import time

import pyautogui
import win32api
import win32con
import win32gui
import win32process

pyautogui.PAUSE = 0
pyautogui.FAILSAFE = False

ROBLOX_CLASS = "WINDOWSCLIENT"
ROBLOX_EXE = "robloxplayerbeta.exe"
_PROCESS_ACCESS = win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ


def find_roblox_window():
    found = []

    def callback(hwnd, _extra):
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return True
            if win32gui.GetClassName(hwnd) != ROBLOX_CLASS:
                return True
            _thread, pid = win32process.GetWindowThreadProcessId(hwnd)
            image = _process_image(pid)
            if os.path.basename(image).lower() == ROBLOX_EXE:
                found.append(hwnd)
        except Exception:
            return True
        return True

    win32gui.EnumWindows(callback, None)
    if not found:
        return None
    return found[0]


def focus_window(hwnd):
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        if win32gui.GetForegroundWindow() == hwnd:
            return True

        foreground = win32gui.GetForegroundWindow()
        fg_thread = 0
        if foreground:
            fg_thread, _pid = win32process.GetWindowThreadProcessId(foreground)
        target_thread, _pid = win32process.GetWindowThreadProcessId(hwnd)
        attached = False
        try:
            if fg_thread and target_thread and fg_thread != target_thread:
                win32process.AttachThreadInput(fg_thread, target_thread, True)
                attached = True
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
        finally:
            if attached:
                win32process.AttachThreadInput(fg_thread, target_thread, False)
    except Exception:
        return False
    return win32gui.GetForegroundWindow() == hwnd


def _move_with_events(x, y, duration):
    backend = pyautogui._pyautogui_win
    flags = backend.MOUSEEVENTF_MOVE | backend.MOUSEEVENTF_ABSOLUTE
    start_x, start_y = win32api.GetCursorPos()
    x = int(x)
    y = int(y)
    if duration <= 0:
        backend._sendMouseEvent(flags, x, y)
        return
    steps = max(1, int(duration / 0.01))
    for step in range(1, steps + 1):
        portion = step / steps
        point_x = int(round(start_x + (x - start_x) * portion))
        point_y = int(round(start_y + (y - start_y) * portion))
        backend._sendMouseEvent(flags, point_x, point_y)
        if step < steps:
            time.sleep(duration / steps)


def client_click(hwnd, x, y, duration=0.5):
    screen_x, screen_y = win32gui.ClientToScreen(hwnd, (int(x), int(y)))
    _move_with_events(screen_x, screen_y, duration)
    pyautogui.click()


def press_key(key):
    pyautogui.press(key)


def hotkey(*keys):
    pyautogui.hotkey(*keys)


def wait(seconds, stop_event):
    stop_event.wait(seconds)


def cursor_client_position(hwnd=None):
    if hwnd is None:
        hwnd = find_roblox_window()
    if not hwnd:
        return None
    return win32gui.ScreenToClient(hwnd, win32api.GetCursorPos())


def _process_image(pid):
    handle = win32api.OpenProcess(_PROCESS_ACCESS, False, pid)
    try:
        return win32process.GetModuleFileNameEx(handle, 0)
    finally:
        win32api.CloseHandle(handle)
