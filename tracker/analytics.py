"""Analytics dashboard for the TWLF time tracker.

The ``AnalyticsView`` window summarises tracked sessions over a chosen
time range, grouping them by application or project and visualising the
results using matplotlib.  This provides high‑level insights into how
time is allocated across tasks.
"""
from __future__ import annotations

import customtkinter as ctk
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

from tracker.data import read_activity_log

try:
    import pandas as pd  # type: ignore[import-not-found]
    import matplotlib
    # Use a non‑interactive backend suitable for embedding in tkinter
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
except Exception:
    pd = None  # pragma: no cover
    FigureCanvasTkAgg = None  # type: ignore


class AnalyticsView(ctk.CTkToplevel):
    """A toplevel window displaying charts summarising tracked time."""

    def __init__(self, parent: ctk.CTk):
        super().__init__(parent)
        self.title("Analytics Dashboard")
        self.geometry("1000x600")
        self.resizable(True, True)

        self.start_date: datetime = datetime.now() - timedelta(days=30)
        self.end_date: Optional[datetime] = None
        # Chart grouping dimension (app or project)
        self.group_by: str = "app"

        self._build_controls()
        self._build_chart_area()
        self.refresh_chart()

    def _build_controls(self) -> None:
        frame = ctk.CTkFrame(self)
        frame.pack(fill="x", padx=10, pady=5)
        # Date range inputs
        ctk.CTkLabel(frame, text="Start date (YYYY-MM-DD):").pack(side="left", padx=2)
        self.start_entry = ctk.CTkEntry(frame, width=100)
        self.start_entry.insert(0, self.start_date.strftime("%Y-%m-%d"))
        self.start_entry.pack(side="left", padx=2)

        ctk.CTkLabel(frame, text="End date (optional):").pack(side="left", padx=2)
        self.end_entry = ctk.CTkEntry(frame, width=100)
        self.end_entry.pack(side="left", padx=2)

        # Group by selector
        ctk.CTkLabel(frame, text="Group by:").pack(side="left", padx=2)
        self.group_var = ctk.StringVar(value=self.group_by)
        opt = ctk.CTkOptionMenu(frame, variable=self.group_var, values=["app", "project"])
        opt.pack(side="left", padx=2)

        btn = ctk.CTkButton(frame, text="Update", command=self.refresh_chart)
        btn.pack(side="left", padx=5)

    def _build_chart_area(self) -> None:
        # Container for the matplotlib figure
        self.chart_frame = ctk.CTkFrame(self)
        self.chart_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.canvas: Optional[FigureCanvasTkAgg] = None

    def refresh_chart(self) -> None:
        """Recompute aggregated statistics and redraw the chart."""
        # Parse inputs
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
        self.group_by = self.group_var.get()

        # Query sessions
        sessions = read_activity_log(start_date=self.start_date, end_date=self.end_date)
        if pd is None or not sessions:
            return
        df = pd.DataFrame(sessions)
        if df.empty:
            return
        # Ensure numeric
        df["duration_sec"] = pd.to_numeric(df["duration_sec"], errors="coerce").fillna(0.0)
        group_col = self.group_by
        # Replace None/NaN with explicit label
        df[group_col] = df[group_col].fillna("(Unassigned)")
        grouped = df.groupby(group_col)["duration_sec"].sum().sort_values(ascending=False)
        # Convert seconds to hours for readability
        grouped_hours = grouped / 3600.0
        # Plot
        fig = plt.Figure(figsize=(6, 4))
        ax = fig.add_subplot(111)
        grouped_hours.plot(kind="bar", ax=ax, color="#336699")
        ax.set_ylabel("Hours")
        ax.set_xlabel(self.group_by.capitalize())
        ax.set_title(f"Time by {self.group_by.capitalize()} ({self.start_date.strftime('%Y-%m-%d')} – "
                     f"{self.end_date.strftime('%Y-%m-%d') if self.end_date else 'Present'})")
        fig.tight_layout()
        # Clear previous canvas
        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        self.canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
