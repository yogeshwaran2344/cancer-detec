"""
PathoGuard-AI — Persistent SQLite Database Connection Layer
Provides thread-safe connections, WAL mode concurrency, and table initialization.
"""

import sqlite3
import os
import contextlib
from typing import Generator

# Database file location in PathoGuard-AI-Backend/data/
DB_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data"
)
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "pathoguard.db")


def get_connection() -> sqlite3.Connection:
    """Creates a configured connection with row factory and WAL mode."""
    conn = sqlite3.connect(DB_PATH, timeout=10.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency between web server and background tasks
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextlib.contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions with automatic commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
