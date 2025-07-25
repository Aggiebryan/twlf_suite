"""
Data layer for the TWLF activity tracker.

This module provides a simple SQLite backend for logging session
information and retrieving or editing those logs.  Using SQLite ensures
durable storage that scales beyond a simple CSV while remaining
lightweight and easy to query.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import List, Optional, Dict, Any, Iterable


# Locate the database alongside this package at project root.  Creating the
# database file outside of the package directory simplifies backups and
# upgrades.
DB_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "twlf_time.db")

# --- Database Schema ---
# Table: sessions
# Columns:
#   id             integer primary key autoincrement
#   date           text         -- calendar date (YYYY‑MM‑DD)
#   start_time     text         -- ISO timestamp when a session starts
#   end_time       text         -- ISO timestamp when a session ends
#   duration_sec   real         -- seconds of activity accumulated
#   app            text         -- user‑friendly app name
#   filetab        text         -- file/tab title or descriptor
#   activity_desc  text         -- optional user‑provided description
#   project        text         -- optional project name
#   tags           text         -- optional comma‑separated tags
#   clio_matter_id text         -- optional Clio matter identifier
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT,
    start_time TEXT,
    end_time TEXT,
    duration_sec REAL,
    app TEXT,
    filetab TEXT,
    activity_desc TEXT,
    project TEXT,
    tags TEXT,
    clio_matter_id TEXT
);
"""


def get_conn() -> sqlite3.Connection:
    """Open a connection to the SQLite database with foreign keys enabled."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Initialise the database schema if it does not already exist."""
    with get_conn() as conn:
        conn.execute(SCHEMA)


# --- Logging and Retrieval ---
def log_activity(
    start_time: datetime,
    end_time: datetime,
    duration_sec: float,
    app: str,
    filetab: str,
    activity_desc: str = "",
    project: Optional[str] = None,
    tags: Optional[Iterable[str] | str] = None,
    clio_matter_id: Optional[str] = None,
) -> int:
    """
    Insert a new session record and return its id.

    :param start_time: A ``datetime`` marking the start of the session.
    :param end_time: A ``datetime`` marking the end of the session.
    :param duration_sec: Total active seconds recorded in the session.
    :param app: User‑friendly application name.
    :param filetab: File or tab name associated with the session.
    :param activity_desc: Optional free‑form description of the activity.
    :param project: Optional project name used for grouping sessions.
    :param tags: Optional iterable or comma‑separated string of tags.
    :param clio_matter_id: Optional identifier linking the session to a Clio matter.
    :return: The primary key of the inserted session.
    """
    date_str = start_time.strftime("%Y-%m-%d")
    start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
    # Normalise tags into a comma‑delimited string for storage
    if tags is None:
        tags_str: Optional[str] = None
    elif isinstance(tags, str):
        tags_str = tags
    else:
        tags_str = ",".join(str(t).strip() for t in tags)
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sessions
            (date, start_time, end_time, duration_sec, app, filetab, activity_desc, project, tags, clio_matter_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_str,
                start_str,
                end_str,
                float(duration_sec),
                app,
                filetab,
                activity_desc,
                project,
                tags_str,
                clio_matter_id,
            ),
        )
        conn.commit()
        return cur.lastrowid


def read_activity_log(
    start_date: datetime,
    end_date: Optional[datetime] = None,
    app: Optional[str] = None,
    project: Optional[str] = None,
    tags: Optional[str] = None,
    clio_matter_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve sessions in a date range, optionally filtered by app, project,
    tags or Clio matter.
    """
    sql = "SELECT * FROM sessions WHERE date >= ?"
    params: list[Any] = [start_date.strftime("%Y-%m-%d")]
    if end_date:
        sql += " AND date <= ?"
        params.append(end_date.strftime("%Y-%m-%d"))
    if app:
        sql += " AND app = ?"
        params.append(app)
    if project:
        sql += " AND project = ?"
        params.append(project)
    if tags:
        # Match tags via LIKE pattern; this simple approach can be improved later.
        sql += " AND tags LIKE ?"
        params.append(f"%{tags}%")
    if clio_matter_id:
        sql += " AND clio_matter_id = ?"
        params.append(clio_matter_id)
    sql += " ORDER BY date, start_time"
    with get_conn() as conn:
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def update_session(session_id: int, **fields: Any) -> None:
    """
    Update arbitrary fields on an existing session.

    Accepts keyword arguments corresponding to column names in the sessions table.
    Only provided fields will be updated.
    """
    if not fields:
        return
    valid_cols = {
        "date",
        "start_time",
        "end_time",
        "duration_sec",
        "app",
        "filetab",
        "activity_desc",
        "project",
        "tags",
        "clio_matter_id",
    }
    assignments = []
    params: list[Any] = []
    for col, val in fields.items():
        if col not in valid_cols:
            raise ValueError(f"Invalid column: {col}")
        # Skip None values (leave unchanged)
        if val is None:
            continue
        assignments.append(f"{col} = ?")
        params.append(val)
    if not assignments:
        return
    params.append(session_id)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE sessions SET {', '.join(assignments)} WHERE id = ?",
            params,
        )
        conn.commit()


def delete_session(session_id: int) -> None:
    """Remove a session record entirely."""
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()


def format_duration(seconds: float) -> str:
    """Format seconds into ``HH:MM:SS`` for display."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# Initialise the database schema on module import.  This ensures the table is
# created when the application first runs.
init_db()
