"""
Entry point for the TWLF time tracker.

This script launches the ``ActivityTrackerApp`` defined in
``tracker.ui``.  Running this file will start the application with
a sidebar for navigation, session editing capabilities, timeline browsing,
analytics and manual event creation.
"""

from tracker.ui import ActivityTrackerApp


def main() -> None:
    """Instantiate and run the primary application window."""
    app = ActivityTrackerApp()
    app.mainloop()


if __name__ == "__main__":
    main()