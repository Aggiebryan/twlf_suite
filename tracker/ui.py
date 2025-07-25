"""User interface for the TWLF time tracker.

This module builds the primary customtkinter window, exposes a sidebar with
navigation to various screens (timeline, editor, analytics), and
integrates with the ``SessionManager`` to display the current activity in
real time.
"""
from __future__ import annotations

import customtkinter as ctk

from tracker.session_manager import SessionManager
from tracker.editor import SessionEditor
from tracker.timeline import TimelineView
from tracker.analytics import AnalyticsView


class ActivityTrackerApp(ctk.CTk):
    """Main application window for the time tracker."""

    def __init__(self) -> None:
        super().__init__()
        self.title("TWLF Time Tracker")
        self.geometry("900x600")

        # Sidebar for navigation
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.pack(side="left", fill="y")

        # Main content area
        self.main = ctk.CTkFrame(self)
        self.main.pack(side="right", expand=True, fill="both")

        self.build_sidebar()

        # Active session tracking
        self.manager = SessionManager()
        # Launch background tracking
        self.manager.start()

        # Label showing current activity
        self.label = ctk.CTkLabel(self.main, text="Tracking activity...", font=ctk.CTkFont(size=20))
        self.label.pack(pady=30)

        self.update_ui_loop()

    def build_sidebar(self) -> None:
        """Create navigation buttons."""
        label = ctk.CTkLabel(self.sidebar, text="Navigation", font=ctk.CTkFont(weight="bold"))
        label.pack(pady=20)

        btn_home = ctk.CTkButton(self.sidebar, text="Home", command=self.show_home)
        btn_home.pack(pady=10, padx=10, fill="x")

        btn_editor = ctk.CTkButton(self.sidebar, text="Edit Sessions", command=self.open_session_editor)
        btn_editor.pack(pady=5, padx=10, fill="x")

        btn_timeline = ctk.CTkButton(self.sidebar, text="Timeline View", command=self.open_timeline_view)
        btn_timeline.pack(pady=5, padx=10, fill="x")

        btn_analytics = ctk.CTkButton(self.sidebar, text="Analytics", command=self.open_analytics_view)
        btn_analytics.pack(pady=5, padx=10, fill="x")

        # Exit button
        btn_exit = ctk.CTkButton(
            self.sidebar,
            text="Exit",
            fg_color="#c72626",
            hover_color="#d23b3b",
            command=self.on_exit,
        )
        btn_exit.pack(pady=(20, 5), padx=10, fill="x")

    def show_home(self) -> None:
        """Return to the home screen showing the active application."""
        for widget in self.main.winfo_children():
            widget.destroy()
        self.label = ctk.CTkLabel(self.main, text="Tracking activity...", font=ctk.CTkFont(size=20))
        self.label.pack(pady=30)

    def update_ui_loop(self) -> None:
        """Periodically update the displayed current activity."""
        # Acquire the most recent session from the manager; fall back to placeholder.
        session = self.manager.get_most_recent()
        if session:
            app_name = session.get("app", "")
            filetab = session.get("window", "")
            text = f"Currently using:\n{app_name} – {filetab}"
        else:
            text = "No active session."
        if hasattr(self, "label"):
            self.label.configure(text=text)
        self.after(3000, self.update_ui_loop)

    def open_session_editor(self) -> None:
        """Open the session editing window."""
        SessionEditor(self)

    def open_timeline_view(self) -> None:
        """Open the timeline/history view."""
        TimelineView(self)

    def open_analytics_view(self) -> None:
        """Open the analytics dashboard."""
        AnalyticsView(self)

    def on_exit(self) -> None:
        """Finalize all sessions and close the application."""
        # Finalize any in‑memory sessions before exiting
        try:
            self.manager.finalize_all()
        except Exception:
            pass
        self.destroy()
