"""Timeline/history viewer for the TWLF time tracker.

The ``TimelineView`` window allows users to browse past sessions, filter
them by date range, application, project or tags, and search through
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

    def __init__(self, parent: ctk.CTk):
        super().__init__(parent)
        self.title("Timeline View")
        self.geometry("1000x600")
        self.resizable(True, True)

        # Default filter values
        self.start_date: datetime = datetime.now() - timedelta(days=30)
        self.end_date: Optional[datetime] = None
        self.filter_app: Optional[str] = None
        self.filter_project: Optional[str] = None
        self.filter_tags: Optional[str] = None

        self._build_filters()
        self._build_list()
        self.apply_filters()

    def _build_filters(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=5)

        # Date filters
        ctk.CTkLabel(frame, text="Start date (YYYY-MM-DD):").pack(side="left", padx=2)
        self.start_entry = ctk.CTkEntry(frame, width=100)
        self.start_entry.insert(0, self.start_date.strftime("%Y-%m-%d"))
        self.start_entry.pack(side="left", padx=2)

        ctk.CTkLabel(frame, text="End date (optional):").pack(side="left", padx=2)
        self.end_entry = ctk.CTkEntry(frame, width=100)
        self.end_entry.pack(side="left", padx=2)

        # App filter
        ctk.CTkLabel(frame, text="App:").pack(side="left", padx=2)
        self.app_entry = ctk.CTkEntry(frame, width=100)
        self.app_entry.pack(side="left", padx=2)

        # Project filter
        ctk.CTkLabel(frame, text="Project:").pack(side="left", padx=2)
        self.project_entry = ctk.CTkEntry(frame, width=100)
        self.project_entry.pack(side="left", padx=2)

        # Tags filter
        ctk.CTkLabel(frame, text="Tags:").pack(side="left", padx=2)
        self.tags_entry = ctk.CTkEntry(frame, width=100)
        self.tags_entry.pack(side="left", padx=2)

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
            ("File/Tab", 180),
            ("Project", 100),
            ("Tags", 120),
            ("Description", 200),
        ]:
            lbl = ctk.CTkLabel(header, text=text)
            lbl.configure(width=width)
            lbl.pack(side="left")

    def apply_filters(self) -> None:
        """Retrieve records based on the current filter inputs and display them."""
        # Parse filters
        try:
            self.start_date = datetime.strptime(self.start_entry.get().strip(), "%Y-%m-%d")
        except Exception:
            self.start_date = datetime.now() - timedelta(days=30)
        end_text = self.end_entry.get().strip()
        if end_text:
            try:
                self.end_date = datetime.strptime(end_text, "%Y-%m-%d")
            except Exception:
                self.end_date = None
        else:
            self.end_date = None
        self.filter_app = self.app_entry.get().strip() or None
        self.filter_project = self.project_entry.get().strip() or None
        self.filter_tags = self.tags_entry.get().strip() or None

        # Query
        sessions = read_activity_log(
            start_date=self.start_date,
            end_date=self.end_date,
            app=self.filter_app,
            project=self.filter_project,
            tags=self.filter_tags,
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
        values = [
            sess.get("date"),
            sess.get("start_time"),
            sess.get("end_time"),
            f"{sess.get('duration_sec'):0.0f}s",
            sess.get("app"),
            sess.get("filetab"),
            sess.get("project") or "",
            sess.get("tags") or "",
            sess.get("activity_desc") or "",
        ]
        widths = [80, 120, 120, 80, 120, 180, 100, 120, 200]
        for val, width in zip(values, widths):
            lbl = ctk.CTkLabel(frame, text=str(val) if val is not None else "")
            lbl.configure(width=width)
            lbl.pack(side="left")
