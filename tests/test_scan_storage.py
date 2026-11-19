"""Unit tests for Phase 2 SQLite database and scan repository."""

import os
import sqlite3
import tempfile
import pytest

from database.connection import get_db_connection, init_db
from database.repository import ScanRepository


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def repo(temp_db):
    return ScanRepository(db_path=temp_db)


class TestScanRepository:
    def test_init_and_empty_state(self, repo):
        assert repo.get_scan_count() == 0
        assert repo.get_recent_scans() == []
        assert repo.get_sync_state("test@example.com") is None
        assert repo.is_message_scanned("test@example.com", "msg-123") is False

    def test_save_and_retrieve_scan_result(self, repo):
        record = {
            "mailbox": "user@example.com",
            "gmail_message_id": "msg_001",
            "gmail_thread_id": "thread_001",
            "sender": "Security Alert <alert@paypal.notice.com>",
            "subject": "Urgent: Your account is suspended",
            "body": "Dear customer, click here to unlock your account immediately.",
            "received_at": "2026-10-30T08:00:00Z",
            "classification": "Phishing",
            "phishing_probability": 0.9421,
            "logistic_regression_probability": 0.9120,
            "lightgbm_probability": 0.9722,
            "inference_time_ms": 12.45,
            "model_version": "v1.0",
        }
        scan_id = repo.save_scan_result(record)
        assert scan_id is not None
        assert scan_id > 0

        assert repo.is_message_scanned("user@example.com", "msg_001") is True
        assert repo.is_message_scanned("user@example.com", "msg_002") is False
        assert repo.is_message_scanned("other@example.com", "msg_001") is False

        assert repo.get_scan_count() == 1
        assert repo.get_scan_count("user@example.com") == 1
        assert repo.get_scan_count("other@example.com") == 0

        recent = repo.get_recent_scans()
        assert len(recent) == 1
        assert recent[0]["gmail_message_id"] == "msg_001"
        assert recent[0]["classification"] == "Phishing"
        assert recent[0]["body"] == "Dear customer, click here to unlock your account immediately."
        assert recent[0]["phishing_probability"] == pytest.approx(0.9421, abs=1e-4)

    def test_duplicate_prevention_raises_integrity_error(self, repo):
        record = {
            "mailbox": "user@example.com",
            "gmail_message_id": "msg_dup",
            "gmail_thread_id": "thread_dup",
            "sender": "support@example.com",
            "subject": "Hello",
            "received_at": "2026-10-30T08:00:00Z",
            "classification": "Legitimate",
            "phishing_probability": 0.05,
            "logistic_regression_probability": 0.04,
            "lightgbm_probability": 0.06,
            "inference_time_ms": 8.1,
            "model_version": "v1.0",
        }
        repo.save_scan_result(record)

        # Attempting duplicate insert with same (mailbox, gmail_message_id) must fail
        with pytest.raises(sqlite3.IntegrityError):
            repo.save_scan_result(record)

    def test_sync_state_persistence_and_update(self, repo, temp_db):
        mailbox = "sync_user@example.com"
        assert repo.get_sync_state(mailbox) is None

        # Insert initial sync state
        repo.update_sync_state(mailbox, last_history_id="10001", last_internal_date=1690000000000)
        state = repo.get_sync_state(mailbox)
        assert state is not None
        assert state["mailbox"] == mailbox
        assert state["last_history_id"] == "10001"
        assert state["last_internal_date"] == 1690000000000

        # Update with newer internal_date
        repo.update_sync_state(mailbox, last_history_id="10050", last_internal_date=1690000500000)
        updated_state = repo.get_sync_state(mailbox)
        assert updated_state["last_history_id"] == "10050"
        assert updated_state["last_internal_date"] == 1690000500000

        # Verify state persistence across new repository instance
        new_repo = ScanRepository(db_path=temp_db)
        reopened_state = new_repo.get_sync_state(mailbox)
        assert reopened_state["last_history_id"] == "10050"
        assert reopened_state["last_internal_date"] == 1690000500000

    def test_save_and_retrieve_risk_tier_and_auth_flags(self, repo, temp_db):
        record = {
            "mailbox": "user@example.com",
            "gmail_message_id": "msg_tier_001",
            "gmail_thread_id": "thread_tier_001",
            "sender": "Facebook <notification@facebookmail.com>",
            "subject": "John Doe commented on your post",
            "received_at": "2026-10-30T08:00:00Z",
            "classification": "Phishing",
            "risk_tier": "Suspicious",
            "phishing_probability": 0.5823,
            "logistic_regression_probability": 0.5510,
            "lightgbm_probability": 0.6136,
            "inference_time_ms": 11.2,
            "model_version": "v1.0",
            "spf_pass": 1,
            "dkim_pass": 1,
            "dmarc_pass": 1,
        }
        scan_id = repo.save_scan_result(record)
        assert scan_id is not None

        conn = get_db_connection(temp_db)
        row = conn.execute("SELECT * FROM email_scans WHERE id = ?", (scan_id,)).fetchone()
        assert row["risk_tier"] == "Suspicious"
        assert row["spf_pass"] == 1
        assert row["dkim_pass"] == 1
        assert row["dmarc_pass"] == 1
        conn.close()

    def test_legacy_database_migration_and_backfill(self, temp_db):
        # Create an unmigrated legacy table without risk_tier / auth columns
        conn = sqlite3.connect(temp_db)
        conn.execute(
            """
            CREATE TABLE email_scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mailbox TEXT NOT NULL,
                gmail_message_id TEXT NOT NULL,
                gmail_thread_id TEXT,
                sender TEXT,
                subject TEXT,
                received_at TEXT NOT NULL,
                classification TEXT NOT NULL,
                phishing_probability REAL NOT NULL,
                logistic_regression_probability REAL NOT NULL,
                lightgbm_probability REAL NOT NULL,
                inference_time_ms REAL NOT NULL,
                scanned_at TEXT NOT NULL,
                model_version TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            INSERT INTO email_scans (
                mailbox, gmail_message_id, received_at, classification,
                phishing_probability, logistic_regression_probability,
                lightgbm_probability, inference_time_ms, scanned_at, model_version
            ) VALUES
            ('m@test.com', 'm1', '2026-01-01', 'Legitimate', 0.15, 0.1, 0.2, 5.0, '2026-01-01', 'v1.0'),
            ('m@test.com', 'm2', '2026-01-01', 'Phishing', 0.62, 0.6, 0.64, 5.0, '2026-01-01', 'v1.0'),
            ('m@test.com', 'm3', '2026-01-01', 'Phishing', 0.88, 0.85, 0.91, 5.0, '2026-01-01', 'v1.0');
            """
        )
        conn.commit()
        conn.close()

        # Run init_db to trigger migration & backfill
        init_db(temp_db)

        conn = get_db_connection(temp_db)
        rows = conn.execute("SELECT gmail_message_id, risk_tier FROM email_scans ORDER BY gmail_message_id").fetchall()
        tier_map = {r["gmail_message_id"]: r["risk_tier"] for r in rows}
        assert tier_map["m1"] == "Legitimate"
        assert tier_map["m2"] == "Suspicious"
        assert tier_map["m3"] == "High-Confidence Phishing"
        conn.close()

