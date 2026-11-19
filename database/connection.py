"""SQLite database connection and initialization for ZanderEtAlFishing."""

import os
import sqlite3
from typing import Optional

DEFAULT_DB_PATH = os.environ.get("DATABASE_PATH", "zander_email_monitor.db")


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection.
    
    Enables WAL mode and sets row factory to sqlite3.Row for dict-like access.
    """
    path = db_path or os.environ.get("DATABASE_PATH", DEFAULT_DB_PATH)
    # Ensure directory exists if path contains directories
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    conn = sqlite3.connect(path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high concurrency and performance
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database tables and indexes if they do not exist."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS email_scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mailbox TEXT NOT NULL,
                    gmail_message_id TEXT NOT NULL,
                    gmail_thread_id TEXT,
                    sender TEXT,
                    subject TEXT,
                    body TEXT,
                    received_at TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    phishing_probability REAL NOT NULL,
                    logistic_regression_probability REAL NOT NULL,
                    lightgbm_probability REAL NOT NULL,
                    inference_time_ms REAL NOT NULL,
                    scanned_at TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    risk_tier TEXT,
                    spf_pass INTEGER,
                    dkim_pass INTEGER,
                    dmarc_pass INTEGER,
                    CONSTRAINT uq_mailbox_message UNIQUE (mailbox, gmail_message_id)
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_email_scans_mailbox_msgid
                ON email_scans(mailbox, gmail_message_id);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_email_scans_scanned_at
                ON email_scans(scanned_at);
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scanner_sync_state (
                    mailbox TEXT PRIMARY KEY,
                    last_history_id TEXT,
                    last_internal_date INTEGER,
                    last_sync_at TEXT NOT NULL,
                    status TEXT DEFAULT 'ACTIVE'
                );
                """
            )

            # Migrate existing databases: add new columns if they don't exist yet.
            # SQLite does not support ADD COLUMN IF NOT EXISTS, so we probe first.
            existing_cols = {
                row[1] for row in conn.execute("PRAGMA table_info(email_scans)").fetchall()
            }
            for col_def in [
                ("risk_tier", "TEXT"),
                ("spf_pass", "INTEGER"),
                ("dkim_pass", "INTEGER"),
                ("dmarc_pass", "INTEGER"),
                ("body", "TEXT"),
            ]:
                if col_def[0] not in existing_cols:
                    conn.execute(
                        f"ALTER TABLE email_scans ADD COLUMN {col_def[0]} {col_def[1]};"
                    )

            # Create index on risk_tier after column is guaranteed to exist
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_email_scans_risk_tier
                ON email_scans(risk_tier);
                """
            )

            # Back-fill risk_tier for any legacy rows that have risk_tier NULL
            conn.execute(
                """
                UPDATE email_scans
                SET risk_tier = CASE
                    WHEN phishing_probability >= 0.70 THEN 'High-Confidence Phishing'
                    WHEN phishing_probability >= 0.50 THEN 'Suspicious'
                    ELSE 'Legitimate'
                END
                WHERE risk_tier IS NULL;
                """
            )
    finally:
        conn.close()

