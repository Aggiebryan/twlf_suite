"""User interface for the TWLF time tracker.

This module builds the primary customtkinter window, exposes a sidebar with
navigation to various screens (timeline, editor, analytics), and
integrates with the ``SessionManager`` to display the current activity in
real time.  Additional enhancements include a manual event button,
appearance mode selector and a logo in the bottom‑right corner.
"""
from __future__ import annotations

import os
import customtkinter as ctk
from PIL import Image  # type: ignore[import-not-found]

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

        # Appearance mode (light/dark)
        ctk.set_appearance_mode("light")

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

        # Manual event button on the home screen
        self.manual_btn = ctk.CTkButton(self.main, text="Add Manual Event", command=self.open_manual_event)
        self.manual_btn.pack(pady=5)

        # Logo in bottom right
        self._add_logo()

        self.update_ui_loop()

    def _add_logo(self) -> None:
        """Display the logo at the bottom right of the main window."""
        try:
            # Attempt to load the provided logo from the project root.
            logo_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "QALS Logo 2.png")
            if os.path.exists(logo_path):
                pil_image = Image.open(logo_path)
                # Resize to a reasonable size
                pil_image = pil_image.resize((80, 80))
                self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image)
                logo_label = ctk.CTkLabel(self.main, image=self.logo_image, text="")
                # Place at bottom right using pack with appropriate paddings
                logo_label.pack(side="bottom", anchor="e", padx=10, pady=10)
        except Exception:
            pass

    def build_sidebar(self) -> None:
        """Create navigation buttons and appearance mode selector."""
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

        # Appearance mode selector
        mode_frame = ctk.CTkFrame(self.sidebar)
        mode_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(mode_frame, text="Mode:").pack(side="left")
        self.mode_var = ctk.StringVar(value="light")
        mode_menu = ctk.CTkOptionMenu(mode_frame, variable=self.mode_var, values=["light", "dark"], command=self._set_mode)
        mode_menu.pack(side="left", padx=5)

        # Exit button
        btn_exit = ctk.CTkButton(
            self.sidebar,
            text="Exit",
            fg_color="#c72626",
            hover_color="#d23b3b",
            command=self.on_exit,
        )
        btn_exit.pack(pady=(20, 5), padx=10, fill="x")

    def _set_mode(self, mode: str) -> None:
        """Change the global appearance mode."""
        if mode.lower() == "dark":
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")

    def show_home(self) -> None:
        """Return to the home screen showing the active application."""
        for widget in self.main.winfo_children():
            widget.destroy()
        self.label = ctk.CTkLabel(self.main, text="Tracking activity...", font=ctk.CTkFont(size=20))
        self.label.pack(pady=30)
        self.manual_btn = ctk.CTkButton(self.main, text="Add Manual Event", command=self.open_manual_event)
        self.manual_btn.pack(pady=5)
        self._add_logo()

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
        """Open the session editing window and bring it to front."""
        editor = SessionEditor(self)
        try:
            editor.focus()
            editor.lift()
        except Exception:
            pass

    def open_timeline_view(self) -> None:
        """Open the timeline/history view and bring it to front."""
        tv = TimelineView(self)
        try:
            tv.focus()
            tv.lift()
        except Exception:
            pass

    def open_analytics_view(self) -> None:
        """Open the analytics dashboard and bring it to front."""
        av = AnalyticsView(self)
        try:
            av.focus()
            av.lift()
        except Exception:
            pass

    def open_manual_event(self) -> None:
        """Open the session editor directly in new entry mode."""
        editor = SessionEditor(self)
        # Immediately open the new session dialog
        try:
            editor._open_new_dialog()  # type: ignore[attr-defined]
        except Exception:
            pass

    def on_exit(self) -> None:
        """Finalize all sessions and close the application."""
        # Finalize any in‑memory sessions before exiting
        try:
            self.manager.finalize_all()
        except Exception:
            pass
        self.destroy()
