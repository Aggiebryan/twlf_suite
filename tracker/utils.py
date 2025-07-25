"""
Utility functions for twlf_suite time tracker.

This module centralises heuristics for naming and filtering windows that
should be logged.  It maps raw process names to friendly application names,
strips unhelpful suffixes from window titles and decides whether a given
application/window should be logged.  Minor adjustments have been made to
improve Outlook naming and to attempt to distinguish between sending and
receiving email windows.
"""
from __future__ import annotations

import os
import re
import win32gui  # type: ignore[import-not-found]
import win32process  # type: ignore[import-not-found]
import psutil  # type: ignore[import-not-found]


# Map of known process names to user‑friendly display names and optional icons.
# Note: Outlook is rendered as "Outlook" rather than the truncated "Olk".
APP_DISPLAY = {
    "WINWORD.EXE": ("MS Word", "msword.ico"),
    "EXCEL.EXE": ("MS Excel", "excel.ico"),
    "POWERPNT.EXE": ("MS PowerPoint", "mspowerpoint.ico"),
    "ONENOTE.EXE": ("MS OneNote", "onenote.ico"),
    "OUTLOOK.EXE": ("Outlook", "outlook.ico"),
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
        with open(EXCLUDE_FILE, 'r', encoding='utf-8') as f:
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

    For Outlook windows, attempt to determine whether the window represents
    a received email or a sent email by examining the second component of
    the title (e.g. ``Subject - Inbox - Outlook`` becomes
    ``From: Subject``).
    """
    p_name = process_name.upper()
    if p_name in APP_DISPLAY:
        display, _ = APP_DISPLAY[p_name]
    else:
        display = process_name.split('.')[0].capitalize()
    file_part = window_title.strip() if window_title else ""

    # Special case for Outlook to differentiate sent vs received messages.
    if display.lower() == "outlook" and " - " in file_part:
        parts = file_part.split(" - ")
        # Outlook window titles often look like "Subject - Inbox - Outlook"
        if len(parts) >= 3:
            subject, folder = parts[0], parts[1]
            folder_lower = folder.strip().lower()
            if folder_lower == "inbox":
                file_part = f"From: {subject}"
            elif folder_lower in ("sent items", "outbox", "drafts"):
                file_part = f"To: {subject}"
            else:
                file_part = subject.strip()

    # Known suffixes for MS apps/browser that we strip.
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
        match = re.match(r"(.+?) and \\d+ more pages", file_part)
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
