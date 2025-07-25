"""Timeline/history viewer for the TWLF time tracker.

The ``TimelineView`` window allows users to browse past sessions, filter
them by date range, application, matter or contact, and search through
their recorded activity.  This is a read‑only view; editing is handled
in ``tracker.editor``.
"""
from __future__ import annotations

import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

from tracker.data import read_activity_log


class TimelineView(ctk.CTkToplevel):
    """A toplevel window for viewing historical session records."""

    def __init__(self, parent: ctk.CTk) -> None:
        super().__init__(parent)
        self.title("Timeline View")
        self.geometry("1000x600")
        self.resizable(True, True)

        # Default filter values
        self.start_date: datetime = datetime.now() - timedelta(days=30)
        self.end_date: Optional[datetime] = None
        self.filter_app: Optional[str] = None
        self.filter_matter: Optional[str] = None
        self.filter_contact: Optional[str] = None

        self._build_filters()
        self._build_list()
        self.apply_filters()

    def _build_filters(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=5)

        # Date filters
        ctk.CTkLabel(frame, text="Start date (MM-DD-YYYY):").pack(side="left", padx=2)
        self.start_entry = ctk.CTkEntry(frame, width=100)
        self.start_entry.insert(0, self.start_date.strftime("%m-%d-%Y"))
        self.start_entry.pack(side="left", padx=2)

        ctk.CTkLabel(frame, text="End date (optional):").pack(side="left", padx=2)
        self.end_entry = ctk.CTkEntry(frame, width=100)
        self.end_entry.pack(side="left", padx=2)

        # App filter
        ctk.CTkLabel(frame, text="App:").pack(side="left", padx=2)
        self.app_entry = ctk.CTkEntry(frame, width=100)
        self.app_entry.pack(side="left", padx=2)

        # Matter filter
        ctk.CTkLabel(frame, text="Matter:").pack(side="left", padx=2)
        self.matter_entry = ctk.CTkEntry(frame, width=100)
        self.matter_entry.pack(side="left", padx=2)

        # Contact filter
        ctk.CTkLabel(frame, text="Contact:").pack(side="left", padx=2)
        self.contact_entry = ctk.CTkEntry(frame, width=100)
        self.contact_entry.pack(side="left", padx=2)

        btn = ctk.CTkButton(frame, text="Search", command=self.apply_filters)
        btn.pack(side="left", padx=5)

    def _build_list(self) -> None:
        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        # Header row
        header = ctk.CTkFrame(self.list_frame)
        header.pack(fill="x", pady=2)
        for text, width in [
            ("Date", 80),
            ("Start", 120),
            ("End", 120),
            ("Duration", 80),
            ("App", 120),
            ("File/Tab", 200),
            ("Matter", 100),
            ("Contact", 120),
            ("Description", 200),
        ]:
            lbl = ctk.CTkLabel(header, text=text)
            lbl.configure(width=width)
            lbl.pack(side="left")

    def apply_filters(self) -> None:
        """Retrieve records based on the current filter inputs and display them."""
        # Parse filters
        try:
            self.start_date = datetime.strptime(self.start_entry.get().strip(), "%m-%d-%Y")
        except Exception:
            self.start_date = datetime.now() - timedelta(days=30)
        end_text = self.end_entry.get().strip()
        if end_text:
            try:
                self.end_date = datetime.strptime(end_text, "%m-%d-%Y")
            except Exception:
                self.end_date = None
        else:
            self.end_date = None
        self.filter_app = self.app_entry.get().strip() or None
        self.filter_matter = self.matter_entry.get().strip() or None
        self.filter_contact = self.contact_entry.get().strip() or None

        # Query
        sessions = read_activity_log(
            start_date=self.start_date,
            end_date=self.end_date,
            app=self.filter_app,
            project=self.filter_matter,
            tags=self.filter_contact,
        )
        # Clear existing
        for widget in self.list_frame.winfo_children()[1:]:
            widget.destroy()
        # Populate rows
        for sess in sessions:
            self._add_row(sess)

    def _add_row(self, sess: Dict[str, Any]) -> None:
        frame = ctk.CTkFrame(self.list_frame)
        frame.pack(fill="x", pady=1)
        # Format date as MM-DD-YYYY
        try:
            date_val = datetime.strptime(str(sess.get("date")), "%Y-%m-%d").strftime("%m-%d-%Y")
        except Exception:
            date_val = sess.get("date")
        # Format times as HH:MM:SS
        def time_only(ts: Any) -> str:
            try:
                return datetime.strptime(str(ts), "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S")
            except Exception:
                return str(ts) if ts is not None else ""
        values = [
            date_val,
            time_only(sess.get("start_time")),
            time_only(sess.get("end_time")),
            f"{sess.get('duration_sec'):0.0f}s",
            sess.get("app"),
            sess.get("filetab"),
            sess.get("project") or "",
            sess.get("tags") or "",
            sess.get("activity_desc") or "",
        ]
        widths = [80, 120, 120, 80, 120, 200, 100, 120, 200]
        for idx, (val, width) in enumerate(zip(values, widths)):
            lbl = ctk.CTkLabel(frame, text=str(val) if val is not None else "", anchor="w")
            lbl.configure(width=width)
            lbl.pack(side="left")
