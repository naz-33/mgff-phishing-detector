"""Data access repository for email scans and scanner synchronization state."""

from datetime import datetime, timezone
import sqlite3
from typing import Any, Dict, List, Optional

from database.connection import get_db_connection, init_db


def utc_now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


class ScanRepository:
    """Repository handling CRUD operations for scan records and sync states."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        init_db(self.db_path)

    def is_message_scanned(self, mailbox: str, gmail_message_id: str) -> bool:
        """Check if a Gmail message has already been scanned for the given mailbox."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM email_scans WHERE mailbox = ? AND gmail_message_id = ? LIMIT 1;",
                (mailbox, gmail_message_id),
            )
            return cursor.fetchone() is not None
        finally:
            conn.close()

    def save_scan_result(self, record: Dict[str, Any]) -> int:
        """Save a new email scan result.
        
        Expected fields in record:
            - mailbox: str
            - gmail_message_id: str
            - gmail_thread_id: Optional[str]
            - sender: Optional[str]
            - subject: Optional[str]
            - body: Optional[str]
            - received_at: str
            - classification: str          (binary: "Phishing" / "Legitimate" — academic ML label)
            - risk_tier: Optional[str]     (operational tier: "Legitimate" / "Suspicious" / "High-Confidence Phishing")
            - phishing_probability: float
            - logistic_regression_probability: float
            - lightgbm_probability: float
            - inference_time_ms: float
            - model_version: str
            - scanned_at: Optional[str]
            - spf_pass: Optional[bool]
            - dkim_pass: Optional[bool]
            - dmarc_pass: Optional[bool]
        """
        scanned_at = record.get("scanned_at") or utc_now_iso()

        conn = get_db_connection(self.db_path)
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO email_scans (
                        mailbox,
                        gmail_message_id,
                        gmail_thread_id,
                        sender,
                        subject,
                        body,
                        received_at,
                        classification,
                        phishing_probability,
                        logistic_regression_probability,
                        lightgbm_probability,
                        inference_time_ms,
                        scanned_at,
                        model_version,
                        risk_tier,
                        spf_pass,
                        dkim_pass,
                        dmarc_pass
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record["mailbox"],
                        record["gmail_message_id"],
                        record.get("gmail_thread_id"),
                        record.get("sender"),
                        record.get("subject"),
                        record.get("body"),
                        record["received_at"],
                        record["classification"],
                        float(record["phishing_probability"]),
                        float(record["logistic_regression_probability"]),
                        float(record["lightgbm_probability"]),
                        float(record["inference_time_ms"]),
                        scanned_at,
                        record["model_version"],
                        record.get("risk_tier"),
                        int(record["spf_pass"]) if record.get("spf_pass") is not None else None,
                        int(record["dkim_pass"]) if record.get("dkim_pass") is not None else None,
                        int(record["dmarc_pass"]) if record.get("dmarc_pass") is not None else None,
                    ),
                )
                return cursor.lastrowid
        finally:
            conn.close()

    def get_sync_state(self, mailbox: str) -> Optional[Dict[str, Any]]:
        """Retrieve the persisted synchronization checkpoint for a mailbox."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT mailbox, last_history_id, last_internal_date, last_sync_at, status
                FROM scanner_sync_state
                WHERE mailbox = ?
                """,
                (mailbox,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        finally:
            conn.close()

    def update_sync_state(
        self,
        mailbox: str,
        last_history_id: Optional[str] = None,
        last_internal_date: Optional[int] = None,
        status: str = "ACTIVE",
    ) -> None:
        """Update or insert the synchronization checkpoint for a mailbox."""
        conn = get_db_connection(self.db_path)
        sync_at = utc_now_iso()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO scanner_sync_state (mailbox, last_history_id, last_internal_date, last_sync_at, status)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(mailbox) DO UPDATE SET
                        last_history_id = COALESCE(excluded.last_history_id, scanner_sync_state.last_history_id),
                        last_internal_date = CASE
                            WHEN excluded.last_internal_date IS NOT NULL AND
                                 (scanner_sync_state.last_internal_date IS NULL OR excluded.last_internal_date > scanner_sync_state.last_internal_date)
                            THEN excluded.last_internal_date
                            ELSE scanner_sync_state.last_internal_date
                        END,
                        last_sync_at = excluded.last_sync_at,
                        status = excluded.status
                    """,
                    (mailbox, last_history_id, last_internal_date, sync_at, status),
                )
        finally:
            conn.close()

    def get_recent_scans(self, mailbox: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent scans ordered by scanned_at descending."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            if mailbox:
                cursor.execute(
                    """
                    SELECT * FROM email_scans
                    WHERE mailbox = ?
                    ORDER BY scanned_at DESC, id DESC
                    LIMIT ?
                    """,
                    (mailbox, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM email_scans
                    ORDER BY scanned_at DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    def get_scan_count(self, mailbox: Optional[str] = None) -> int:
        """Return total number of scan records."""
        conn = get_db_connection(self.db_path)
        try:
            cursor = conn.cursor()
            if mailbox:
                cursor.execute("SELECT COUNT(*) FROM email_scans WHERE mailbox = ?", (mailbox,))
            else:
                cursor.execute("SELECT COUNT(*) FROM email_scans")
            return cursor.fetchone()[0]
        finally:
            conn.close()

    def update_email_body(self, email_id: int, body: str) -> None:
        """Update and cache email body for a specific scan record."""
        conn = get_db_connection(self.db_path)
        try:
            with conn:
                conn.execute(
                    "UPDATE email_scans SET body = ? WHERE id = ?",
                    (body, email_id),
                )
        finally:
            conn.close()

