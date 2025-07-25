"""Session editing interface for the TWLF time tracker.

This module exposes a ``SessionEditor`` window where users can review
previously recorded sessions, modify their details, delete unwanted
entries, or add entirely new sessions.  Sessions can be assigned to
projects and tagged for easier organisation.  All changes are
immediately persisted to the underlying SQLite database via
``tracker.data``.
"""
from __future__ import annotations

import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Optional, Iterable, Dict, Any

from tracker.data import (
    read_activity_log,
    update_session,
    delete_session,
    log_activity,
)


class SessionEditor(ctk.CTkToplevel):
    """A toplevel window for reviewing and editing session entries."""

    def __init__(self, parent: ctk.CTk):
        super().__init__(parent)
        self.title("Session Editor")
        self.geometry("1000x600")
        self.resizable(True, True)

        # Store date range filters; default to last 30 days
        self.start_date: datetime = datetime.now() - timedelta(days=30)
        self.end_date: Optional[datetime] = None

        # Build UI
        self._build_filters()
        self._build_session_list()
        self._build_actions()
        self.refresh_sessions()

    def _build_filters(self) -> None:
        """Create date filter controls at the top of the window."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=5)

        lbl = ctk.CTkLabel(frame, text="Filter start date (YYYY-MM-DD):")
        lbl.pack(side="left", padx=5)
        self.start_entry = ctk.CTkEntry(frame, width=120)
        self.start_entry.insert(0, self.start_date.strftime("%Y-%m-%d"))
        self.start_entry.pack(side="left", padx=5)

        lbl2 = ctk.CTkLabel(frame, text="End date (YYYY-MM-DD, optional):")
        lbl2.pack(side="left", padx=5)
        self.end_entry = ctk.CTkEntry(frame, width=120)
        self.end_entry.pack(side="left", padx=5)

        btn = ctk.CTkButton(frame, text="Apply", command=self.apply_filters)
        btn.pack(side="left", padx=10)

    def _build_session_list(self) -> None:
        """Create the scrollable frame that will hold session rows."""
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Header row
        header = ctk.CTkFrame(self.list_frame)
        header.pack(fill="x", pady=2)
        for text, width in [
            ("ID", 40),
            ("Date", 80),
            ("Start", 120),
            ("End", 120),
            ("Duration", 80),
            ("App", 120),
            ("File/Tab", 180),
            ("Project", 100),
            ("Tags", 100),
        ]:
            lbl = ctk.CTkLabel(header, text=text)
            lbl.configure(width=width)
            lbl.pack(side="left")
        # Placeholder for action column
        ctk.CTkLabel(header, text="Actions", width=140).pack(side="left")

    def _build_actions(self) -> None:
        """Create buttons for adding new sessions."""
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=5)
        add_btn = ctk.CTkButton(frame, text="Add New Session", command=self._open_new_dialog)
        add_btn.pack(side="left", padx=5)

    def apply_filters(self) -> None:
        """Parse filter entries and refresh the list."""
        try:
            start_date = datetime.strptime(self.start_entry.get().strip(), "%Y-%m-%d")
        except Exception:
            start_date = datetime.now() - timedelta(days=30)
        self.start_date = start_date
        end_text = self.end_entry.get().strip()
        if end_text:
            try:
                self.end_date = datetime.strptime(end_text, "%Y-%m-%d")
            except Exception:
                self.end_date = None
        else:
            self.end_date = None
        self.refresh_sessions()

    def refresh_sessions(self) -> None:
        """Populate the scrollable list with sessions from the database."""
        # Clear existing rows (except header)
        for widget in self.list_frame.winfo_children()[1:]:
            widget.destroy()
        sessions = read_activity_log(self.start_date, self.end_date)
        for sess in sessions:
            self._add_session_row(sess)

    def _add_session_row(self, sess: Dict[str, Any]) -> None:
        """Create a row widget for a single session record."""
        frame = ctk.CTkFrame(self.list_frame)
        frame.pack(fill="x", pady=1)
        # Build labels for each column
        values = [
            sess.get("id"),
            sess.get("date"),
            sess.get("start_time"),
            sess.get("end_time"),
            f"{sess.get('duration_sec'):0.0f}s",  # raw seconds for brevity
            sess.get("app"),
            sess.get("filetab"),
            sess.get("project") or "",
            sess.get("tags") or "",
        ]
        widths = [40, 80, 120, 120, 80, 120, 180, 100, 100]
        for val, width in zip(values, widths):
            lbl = ctk.CTkLabel(frame, text=str(val) if val is not None else "")
            lbl.configure(width=width)
            lbl.pack(side="left")
        # Action buttons
        action_frame = ctk.CTkFrame(frame)
        action_frame.pack(side="left", padx=5)
        edit_btn = ctk.CTkButton(action_frame, text="Edit", width=60,
                                 command=lambda s=sess: self._open_edit_dialog(s))
        edit_btn.pack(side="left", padx=2)
        del_btn = ctk.CTkButton(action_frame, text="Delete", width=60,
                                command=lambda sid=sess.get("id"): self._delete_session(sid))
        del_btn.pack(side="left", padx=2)

    def _delete_session(self, session_id: int) -> None:
        """Delete a session and refresh the list."""
        if session_id is None:
            return
        delete_session(session_id)
        self.refresh_sessions()

    def _open_new_dialog(self) -> None:
        """Open a dialog for creating a new session entry."""
        self._open_edit_dialog(None)

    def _open_edit_dialog(self, session: Optional[Dict[str, Any]]) -> None:
        """Open a modal window allowing the user to edit or create a session."""
        dlg = ctk.CTkToplevel(self)
        dlg.title("New Session" if session is None else f"Edit Session #{session.get('id')}")
        dlg.geometry("500x400")
        dlg.resizable(False, False)

        # Helper to extract or default values
        def get_field(key: str, default: str = "") -> str:
            return str(session.get(key)) if session and session.get(key) is not None else default

        # Build form entries
        labels = [
            ("Date (YYYY-MM-DD)", "date"),
            ("Start time (YYYY-MM-DD HH:MM:SS)", "start_time"),
            ("End time (YYYY-MM-DD HH:MM:SS)", "end_time"),
            ("Duration (seconds)", "duration_sec"),
            ("App", "app"),
            ("File/Tab", "filetab"),
            ("Description", "activity_desc"),
            ("Project", "project"),
            ("Tags (comma separated)", "tags"),
            ("Clio Matter ID", "clio_matter_id"),
        ]
        entries: Dict[str, ctk.CTkEntry] = {}
        for idx, (label, key) in enumerate(labels):
            row = ctk.CTkFrame(dlg)
            row.pack(fill="x", padx=10, pady=2)
            lbl = ctk.CTkLabel(row, text=label, width=180)
            lbl.pack(side="left")
            ent = ctk.CTkEntry(row)
            ent.pack(side="left", fill="x", expand=True)
            ent.insert(0, get_field(key))
            entries[key] = ent

        # Save button callback
        def save():
            data: Dict[str, Any] = {k: v.get().strip() or None for k, v in entries.items()}
            # Convert date/time fields
            try:
                if data["date"]:
                    # ensure date only
                    datetime.strptime(data["date"], "%Y-%m-%d")
                if data["start_time"]:
                    datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
                if data["end_time"]:
                    datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass
            # Persist
            if session is None:
                # On creation, if duration not provided, compute from start and end times
                dur = data.get("duration_sec")
                if not dur and data.get("start_time") and data.get("end_time"):
                    try:
                        st = datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
                        et = datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S")
                        dur = (et - st).total_seconds()
                    except Exception:
                        dur = 0.0
                try:
                    dur_val = float(dur) if dur else 0.0
                except Exception:
                    dur_val = 0.0
                log_activity(
                    start_time=datetime.strptime(data["start_time"], "%Y-%m-%d %H:%M:%S")
                    if data.get("start_time")
                    else datetime.now(),
                    end_time=datetime.strptime(data["end_time"], "%Y-%m-%d %H:%M:%S")
                    if data.get("end_time")
                    else datetime.now(),
                    duration_sec=dur_val,
                    app=data.get("app") or "Manual",
                    filetab=data.get("filetab") or "",
                    activity_desc=data.get("activity_desc") or "",
                    project=data.get("project") or None,
                    tags=data.get("tags") or None,
                    clio_matter_id=data.get("clio_matter_id") or None,
                )
            else:
                # Editing existing session
                sid = session.get("id")
                if sid is not None:
                    # Only update provided fields
                    update_session(
                        sid,
                        date=data.get("date"),
                        start_time=data.get("start_time"),
                        end_time=data.get("end_time"),
                        duration_sec=float(data.get("duration_sec")) if data.get("duration_sec") else None,
                        app=data.get("app"),
                        filetab=data.get("filetab"),
                        activity_desc=data.get("activity_desc"),
                        project=data.get("project"),
                        tags=data.get("tags"),
                        clio_matter_id=data.get("clio_matter_id"),
                    )
            dlg.destroy()
            self.refresh_sessions()

        save_btn = ctk.CTkButton(dlg, text="Save", command=save)
        save_btn.pack(pady=10)
