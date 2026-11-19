"""Database service layer querying the existing SQLite database for API endpoints."""

import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from backend.config import DATABASE_PATH
from database.connection import get_db_connection, init_db


class DatabaseService:
    """Service providing aggregated and queried views of the email_scans database."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_PATH
        # Ensure DB tables exist
        init_db(self.db_path)

    def get_connection(self) -> sqlite3.Connection:
        """Obtain a SQLite connection with dict-like row factory."""
        return get_db_connection(self.db_path)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Compute top-level summary metrics from actual email_scans table."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            # Total counts and classifications
            cursor.execute(
                """
                SELECT
                    COUNT(*) as total_scanned,
                    SUM(CASE WHEN classification = 'Phishing' THEN 1 ELSE 0 END) as total_phishing,
                    SUM(CASE WHEN classification = 'Legitimate' THEN 1 ELSE 0 END) as total_legitimate,
                    SUM(CASE WHEN risk_tier = 'Suspicious' THEN 1 ELSE 0 END) as total_suspicious,
                    AVG(inference_time_ms) as avg_latency,
                    MAX(scanned_at) as latest_scan
                FROM email_scans
                """
            )
            row = cursor.fetchone()

            total = row["total_scanned"] or 0
            phishing = row["total_phishing"] or 0
            legitimate = row["total_legitimate"] or 0
            suspicious = row["total_suspicious"] or 0
            avg_latency = round(float(row["avg_latency"] or 0.0), 2)
            latest_scan = row["latest_scan"]

            phishing_ratio = round((phishing / total * 100), 2) if total > 0 else 0.0

            # Get mailbox from sync state or newest email
            cursor.execute("SELECT mailbox, status, last_sync_at FROM scanner_sync_state LIMIT 1")
            sync_row = cursor.fetchone()
            mailbox = sync_row["mailbox"] if sync_row else None
            scanner_status = sync_row["status"] if sync_row else "IDLE"

            if not mailbox and total > 0:
                cursor.execute("SELECT mailbox FROM email_scans ORDER BY id DESC LIMIT 1")
                mb_row = cursor.fetchone()
                if mb_row:
                    mailbox = mb_row["mailbox"]

            # Recent high-confidence phishing warnings (risk_tier = 'High-Confidence Phishing', up to 5)
            # Falls back to classification = 'Phishing' for rows that pre-date the risk_tier migration.
            cursor.execute(
                """
                SELECT * FROM email_scans
                WHERE risk_tier = 'High-Confidence Phishing'
                   OR (risk_tier IS NULL AND classification = 'Phishing')
                ORDER BY scanned_at DESC, id DESC
                LIMIT 5
                """
            )
            recent_warnings = [dict(r) for r in cursor.fetchall()]

            # Recent scans (up to 5)
            cursor.execute(
                """
                SELECT * FROM email_scans
                ORDER BY scanned_at DESC, id DESC
                LIMIT 5
                """
            )
            recent_scans = [dict(r) for r in cursor.fetchall()]

            return {
                "total_scanned": total,
                "total_phishing": phishing,
                "total_legitimate": legitimate,
                "total_suspicious": suspicious,
                "phishing_ratio_percent": phishing_ratio,
                "average_latency_ms": avg_latency,
                "latest_scan_at": latest_scan,
                "mailbox": mailbox,
                "scanner_status": scanner_status,
                "recent_phishing_warnings": recent_warnings,
                "recent_scans": recent_scans,
            }
        finally:
            conn.close()

    def get_emails(
        self,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        classification: Optional[str] = None,
        sort_by: str = "received_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Fetch paginated, filtered, and sorted scanned emails."""
        page = max(1, page)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            conditions: List[str] = []
            params: List[Any] = []

            if classification:
                cl = classification.lower()
                if cl in ("phishing", "legitimate"):
                    conditions.append("LOWER(classification) = ?")
                    params.append(cl)
                elif cl == "suspicious":
                    # Suspicious tier: risk_tier column, or legacy rows without risk_tier
                    # where the probability falls in the boundary zone [0.50, 0.70).
                    conditions.append(
                        "(risk_tier = 'Suspicious' OR "
                        "(risk_tier IS NULL AND classification = 'Phishing' "
                        "AND phishing_probability >= 0.5 AND phishing_probability < 0.7))"
                    )
                elif cl in ("high-confidence phishing", "high_confidence_phishing"):
                    conditions.append(
                        "(risk_tier = 'High-Confidence Phishing' OR "
                        "(risk_tier IS NULL AND classification = 'Phishing' "
                        "AND phishing_probability >= 0.7))"
                    )

            if search and search.strip():
                pattern = f"%{search.strip()}%"
                conditions.append("(subject LIKE ? OR sender LIKE ?)")
                params.extend([pattern, pattern])

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Count total matching rows
            count_query = f"SELECT COUNT(*) FROM email_scans {where_clause}"
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]

            # Allowed sort columns
            allowed_sorts = {
                "received_at": "received_at",
                "scanned_at": "scanned_at",
                "phishing_probability": "phishing_probability",
                "inference_time_ms": "inference_time_ms",
                "subject": "subject",
                "sender": "sender",
            }
            sort_column = allowed_sorts.get(sort_by, "received_at")
            order_dir = "ASC" if sort_order.lower() == "asc" else "DESC"

            query = f"""
                SELECT * FROM email_scans
                {where_clause}
                ORDER BY {sort_column} {order_dir}, id DESC
                LIMIT ? OFFSET ?
            """
            cursor.execute(query, params + [page_size, offset])
            items = [dict(r) for r in cursor.fetchall()]

            total_pages = (total + page_size - 1) // page_size if total > 0 else 1
            return items, total, total_pages
        finally:
            conn.close()

    def get_email_by_id(self, email_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single scanned email details by primary key."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM email_scans WHERE id = ?", (email_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def update_email_body(self, email_id: int, body: str) -> None:
        """Update and cache email body for a specific scan record."""
        conn = self.get_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE email_scans SET body = ? WHERE id = ?",
                    (body, email_id),
                )
        finally:
            conn.close()

    def get_analytics_overview(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Aggregate time-series and distributions from scanned records."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()

            conditions: List[str] = []
            params: List[Any] = []

            if start_date:
                conditions.append("scanned_at >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("scanned_at <= ?")
                params.append(end_date)

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            # Time series grouped by scanned day (YYYY-MM-DD)
            cursor.execute(
                f"""
                SELECT
                    SUBSTR(scanned_at, 1, 10) as scan_date,
                    COUNT(*) as total_scanned,
                    SUM(CASE WHEN classification = 'Phishing' THEN 1 ELSE 0 END) as phishing,
                    SUM(CASE WHEN classification = 'Legitimate' THEN 1 ELSE 0 END) as legitimate,
                    AVG(inference_time_ms) as avg_latency
                FROM email_scans
                {where_clause}
                GROUP BY scan_date
                ORDER BY scan_date ASC
                """,
                params,
            )
            time_series = [
                {
                    "date": r["scan_date"] or "Unknown",
                    "total_scanned": r["total_scanned"],
                    "phishing": r["phishing"],
                    "legitimate": r["legitimate"],
                    "average_latency_ms": round(float(r["avg_latency"] or 0.0), 2),
                }
                for r in cursor.fetchall()
            ]

            # Overall distribution
            cursor.execute(
                f"""
                SELECT
                    SUM(CASE WHEN classification = 'Phishing' THEN 1 ELSE 0 END) as phishing,
                    SUM(CASE WHEN classification = 'Legitimate' THEN 1 ELSE 0 END) as legitimate
                FROM email_scans
                {where_clause}
                """,
                params,
            )
            dist_row = cursor.fetchone()
            phishing_count = dist_row["phishing"] or 0
            legit_count = dist_row["legitimate"] or 0
            total_count = phishing_count + legit_count

            distribution = {
                "phishing": phishing_count,
                "legitimate": legit_count,
                "phishing_percentage": round((phishing_count / total_count * 100), 2) if total_count > 0 else 0.0,
                "legitimate_percentage": round((legit_count / total_count * 100), 2) if total_count > 0 else 0.0,
            }

            # Latency trends (percentiles and distribution)
            cursor.execute(
                f"""
                SELECT inference_time_ms, classification, scanned_at
                FROM email_scans
                {where_clause}
                ORDER BY scanned_at DESC
                LIMIT 50
                """,
                params,
            )
            latency_trends = [
                {
                    "latency_ms": round(float(r["inference_time_ms"]), 2),
                    "classification": r["classification"],
                    "timestamp": r["scanned_at"],
                }
                for r in cursor.fetchall()
            ]

            # Publication research benchmark results from thesis experimental validation
            research_benchmark = {
                "title": "Thesis Experimental Model Performance Benchmark",
                "dataset": "Benchmarked Multi-Source Phishing Corpus (61,000+ emails)",
                "metrics": [
                    {
                        "metric": "Accuracy",
                        "baseline_replication": "95.79%",
                        "proposed_hybrid": "99.12%",
                        "delta": "+3.33%",
                    },
                    {
                        "metric": "Precision",
                        "baseline_replication": "0.9528",
                        "proposed_hybrid": "0.9904",
                        "delta": "+0.0376",
                    },
                    {
                        "metric": "Recall",
                        "baseline_replication": "0.9437",
                        "proposed_hybrid": "0.9921",
                        "delta": "+0.0484",
                    },
                    {
                        "metric": "F1-Score",
                        "baseline_replication": "0.9482",
                        "proposed_hybrid": "0.9912",
                        "delta": "+0.0430",
                    },
                    {
                        "metric": "ROC-AUC",
                        "baseline_replication": "0.9810",
                        "proposed_hybrid": "0.9989",
                        "delta": "+0.0179",
                    },
                    {
                        "metric": "Average Precision (AP)",
                        "baseline_replication": "0.9750",
                        "proposed_hybrid": "0.9987",
                        "delta": "+0.0237",
                    },
                ],
                "confusion_matrix": {
                    "true_negatives": 6052,
                    "false_positives": 59,
                    "false_negatives": 49,
                    "true_positives": 6116,
                },
                "roc_auc": 0.9989,
                "avg_precision": 0.9987,
                "latency_ms": 0.082,
                "note": (
                    "Notice: These metrics represent verified thesis experimental benchmark evaluations "
                    "on labeled test datasets. They are kept strictly separate from the live unlabeled "
                    "Gmail monitoring streams shown above."
                ),
            }

            return {
                "time_series": time_series,
                "distribution": distribution,
                "latency_trends": latency_trends,
                "research_benchmark": research_benchmark,
            }
        finally:
            conn.close()

    def get_monitor_state(self) -> Dict[str, Any]:
        """Fetch current synchronization checkpoint and mailbox configuration."""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scanner_sync_state LIMIT 1")
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {
                "mailbox": None,
                "last_history_id": None,
                "last_internal_date": None,
                "last_sync_at": None,
                "status": "INITIALIZING",
            }
        finally:
            conn.close()

