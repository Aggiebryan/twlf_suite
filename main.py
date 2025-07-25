"""Entry point for the TWLF time tracker.

This script launches the full‑featured ``ActivityTrackerApp`` defined in
``tracker.ui``.  Running this file will start the application with a
sidebar for navigation, session editing capabilities, timeline browsing
and analytics.  The legacy simple tracker UI has been replaced by a
modular implementation built on customtkinter.
"""

from tracker.ui import ActivityTrackerApp


def main() -> None:
    # Instantiate and run the primary application window
    app = ActivityTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
