"""
Utility functions for twlf_suite time tracker:

* App/process/window title parsing
* Exclusion logic
* Foreground window info
* Miscellaneous formatters

These functions wrap platform‑specific APIs (via win32gui, win32process and
psutil) and centralise heuristics for naming and filtering windows that
should be logged.
"""
from __future__ import annotations

import os
import re
import win32gui
import win32process
import psutil


# Map of known process names to user‑friendly display names and optional icons.
APP_DISPLAY = {
    "WINWORD.EXE": ("MS Word", "msword.ico"),
    "EXCEL.EXE": ("MS Excel", "excel.ico"),
    "POWERPNT.EXE": ("MS PowerPoint", "mspowerpoint.ico"),
    "ONENOTE.EXE": ("MS OneNote", "onenote.ico"),
    "OUTLOOK.EXE": ("MS Outlook", "outlook.ico"),
    "CHROME.EXE": ("Chrome", "chrome.ico"),
    "MSEDGE.EXE": ("MS Edge", "msedge.ico"),
    "FIREFOX.EXE": ("Firefox", "firefox.ico"),
    "ACRORD32.EXE": ("Adobe Reader", "adobe.ico"),
    "NOTEPAD.EXE": ("Notepad", "notepad.ico"),
    "EXPLORER.EXE": ("File Explorer", "explorer.ico"),
    "Manual": ("Manual", "manual.ico"),
}


# File listing processes to exclude from logging.
EXCLUDE_FILE = "excluded_processes.txt"


def load_excluded_procs() -> list[str]:
    """Load a list of process names that should not be logged."""
    if os.path.exists(EXCLUDE_FILE):
        with open(EXCLUDE_FILE, 'r') as f:
            return [line.strip().lower() for line in f if line.strip()]
    return []


def should_exclude(process_name: str, window_title: str) -> bool:
    """
    Determine whether a particular process/window should be excluded from logging.

    We filter by both the process name (against a user‑maintained list) and
    certain generic window titles that correspond to system UI elements.
    """
    pn = process_name.lower()
    wt = window_title.lower()
    excluded_procs = load_excluded_procs()
    excluded_titles = [
        "program manager",
        "system tray",
        "overflow window",
        "action center",
        "start menu",
        "task switching",
    ]
    if pn in excluded_procs:
        return True
    if any(pattern in wt for pattern in excluded_titles):
        return True
    return False


def process_and_title(process_name: str, window_title: str) -> tuple[str, str]:
    """
    Convert a raw process name and window title into a user‑friendly
    application name and a cleaned file/tab title.
    """
    p_name = process_name.upper()
    if p_name in APP_DISPLAY:
        display, _ = APP_DISPLAY[p_name]
    else:
        display = process_name.split('.')[0].capitalize()
    file_part = window_title.strip() if window_title else ""
    # Known suffixes for MS apps/browser
    known_suffixes = [
        " - Word",
        " - Excel",
        " - PowerPoint",
        " - OneNote",
        " - Outlook",
        " - Adobe Acrobat Reader",
        " - Notepad",
        " - Google Chrome",
        " - Microsoft Edge",
        " - Mozilla Firefox",
    ]
    for suff in known_suffixes:
        if file_part.endswith(suff):
            file_part = file_part[:-len(suff)].strip()
    # Browsers: remove "and N more pages" and trailing page counts.
    if display in ("MS Edge", "Chrome", "Firefox"):
        match = re.match(r"(.+?) and \d+ more pages", file_part)
        if match:
            file_part = match.group(1).strip()
        if " - " in file_part:
            parts = file_part.split(" - ")
            file_part = parts[0].strip()
    file_part = file_part.replace('\u200b', '').strip()
    return display, file_part


def should_log_app_file(app: str, file_part: str) -> bool:
    """
    Hook to decide if a given (app, file) combination should be logged.
    
    The default implementation logs everything; override this to implement
    per‑application logic.
    """
    return True


def get_foreground_window():
    """
    Return (hwnd, process_name, window_title) for the active foreground window
    or ``None`` if the window should not be logged.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            process_name = process.name()
            if should_exclude(process_name, window_title):
                return None
            app, file_part = process_and_title(process_name, window_title)
            if not should_log_app_file(app, file_part):
                return None
            return hwnd, process_name, window_title
    except Exception:
        return None
    return None
