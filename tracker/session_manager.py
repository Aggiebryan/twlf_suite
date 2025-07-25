"""
High-level session management for the TWLF time tracker.

The ``SessionManager`` coordinates the creation and tracking of in-memory
activity sessions based on foreground window changes.  It is decoupled
from storage concerns; once a session becomes inactive for a period of
time, it is persisted to the database via ``tracker.data.log_activity``.

Modifications from the original implementation include retaining the
last meaningful file/tab name for Microsoft applications so that
intermediate window steps (e.g. ``File Naming``, ``Document3``, ``Save New Document``)
are folded into the same session as the final document name.  The
inactivity limit defaults to five minutes so that switching to another
application temporarily does not prematurely close the session.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock
from typing import Optional, Tuple, Any

from tracker.data import log_activity  # persistent storage function


class SessionManager:
    """
    Manages time tracking sessions (start, update, pause, finalise).
    Persists to SQLite via ``tracker.data.log_activity`` when sessions end.
    """

    def __init__(self, inactivity_limit: timedelta = timedelta(minutes=5)) -> None:
        # mapping from (hwnd, app, window) to session state
        self.sessions: dict[Tuple[int, str, str], dict[str, Any]] = {}
        self.lock = Lock()
        self.active_key: Optional[Tuple[int, str, str]] = None
        self.inactivity_limit = inactivity_limit
        # Track the last non‑transitional file/tab for each application to fold
        # intermediate MS Office windows into the same session.
        self.last_filetab: dict[str, str] = {}

    def _normalise_filetab(self, app: str, file_part: str) -> str:
        """
        Given an application name and a raw file/tab string, return a
        canonicalised file/tab suitable for session grouping.

        For Microsoft Office applications we treat certain transitional
        window titles (e.g. ``File Naming``, ``Document3``, ``Save New Document``,
        ``Uploading to Server``) as part of the same document.  In those
        cases we return the last known file/tab name for the app.
        """
        transitional_phrases = [
            "file naming",
            "document",
            "save new document",
            "uploading to server",
            "unsaved document",
        ]
        # If the file_part contains any transitional phrase and we have a previous
        # real file tab for this app, return that instead.
        lower = file_part.lower()
        if any(lower.startswith(tp) for tp in transitional_phrases):
            return self.last_filetab.get(app, file_part)
        # Otherwise update the last_filetab cache and return as-is.
        if file_part:
            self.last_filetab[app] = file_part
        return file_part

    def update_active(self, active_window: Optional[Tuple[int, str, str]], process_and_title, should_log_app_file) -> None:
        """
        Update or create a session for the currently active window.
        ``active_window`` should be a tuple of (hwnd, process_name, window_title).
        """
        now = datetime.now()
        with self.lock:
            if active_window:
                hwnd, process_name, window_title = active_window
                app, file_part = process_and_title(process_name, window_title)
                # Fold transitional file names into the last known file for this app.
                file_part = self._normalise_filetab(app, file_part)
                key = (hwnd, app, file_part)
                # Pause previous session if changed
                if self.active_key and self.active_key != key and self.active_key in self.sessions:
                    # Only mark paused_at; do not finalise immediately so the session
                    # remains open for the configured inactivity period.
                    self.sessions[self.active_key]["paused_at"] = now
                # Start or resume session for new active window
                if key not in self.sessions:
                    self.sessions[key] = {
                        "date": now.date(),
                        "start_time": now,
                        "last_seen": now,
                        "accumulated": 0.0,
                        "app": app,
                        "window": file_part,
                        "paused_at": None,
                    }
                else:
                    session = self.sessions[key]
                    if session["paused_at"]:
                        session["last_seen"] = now
                        session["paused_at"] = None
                    else:
                        session["last_seen"] = now
                self.active_key = key
                # Accumulate time for the current session; update every two seconds.
                for k in self.sessions:
                    if k == key:
                        self.sessions[k]["accumulated"] += 2.0  # 2‑second interval
            else:
                self.active_key = None

    def finalize_inactive(self) -> None:
        """Persist sessions that have been inactive beyond the inactivity limit."""
        now = datetime.now()
        finalized: list[Tuple[int, str, str]] = []
        with self.lock:
            for key, session in list(self.sessions.items()):
                if session.get("paused_at") and (now - session["paused_at"] > self.inactivity_limit):
                    log_activity(
                        session["start_time"],
                        session["paused_at"],
                        session["accumulated"],
                        session["app"],
                        session["window"],
                        "",  # activity_desc (optional)
                    )
                    finalized.append(key)
            for key in finalized:
                del self.sessions[key]

    def finalize_all(self) -> None:
        """Persist every in‑memory session, typically on application exit."""
        now = datetime.now()
        with self.lock:
            for key, session in list(self.sessions.items()):
                # If the session was never paused, use the last time we saw activity
                end_time = session.get("paused_at") or session.get("last_seen") or now
                log_activity(
                    session["start_time"],
                    end_time,
                    session["accumulated"],
                    session["app"],
                    session["window"],
                    "",  # activity_desc (optional)
                )
            self.sessions.clear()

    def get_most_recent(self) -> Optional[dict[str, Any]]:
        """Return the most recently active session, if any."""
        with self.lock:
            if not self.sessions:
                return None
            latest = max(self.sessions.values(), key=lambda s: s["last_seen"])
            return latest

    def start(self) -> None:
        """
        Launch a background thread that continually polls the foreground window
        and updates session state.  This allows the tracker to run without
        blocking the UI.
        """
        import threading
        import time
        from tracker.utils import get_foreground_window, process_and_title, should_log_app_file

        def worker() -> None:
            while True:
                window = get_foreground_window()
                self.update_active(window, process_and_title, should_log_app_file)
                self.finalize_inactive()
                # Poll every two seconds to balance accuracy and overhead.
                time.sleep(2)

        threading.Thread(target=worker, daemon=True).start()
