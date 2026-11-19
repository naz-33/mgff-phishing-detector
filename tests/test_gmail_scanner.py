"""Comprehensive unit and integration tests for Gmail API integration and EmailScanner."""

import base64
import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest

from database.repository import ScanRepository
from gmail_integration.auth import get_gmail_credentials, validate_credentials_file, SCOPES
from gmail_integration.email_parser import ParsedEmail
from gmail_integration.gmail_client import GmailClient
from gmail_integration.scanner import EmailScanner
from ml_engine.predictor import PhishingPredictor, get_default_predictor


def b64url(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode("utf-8")).decode("utf-8").rstrip("=")


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


@pytest.fixture(scope="module")
def predictor():
    return get_default_predictor()


def create_mock_message(
    msg_id: str,
    subject: str,
    body: str,
    sender: str = "sender@example.com",
    internal_date_ms: int = 1730000000000,
) -> dict:
    return {
        "id": msg_id,
        "threadId": f"thread_{msg_id}",
        "internalDate": str(internal_date_ms),
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": subject},
                {"name": "From", "value": sender},
                {"name": "Date", "value": "Wed, 30 Oct 2026 08:00:00 +0000"},
            ],
            "body": {"data": b64url(body)},
        },
    }


class TestOAuthValidation:
    """Tests for OAuth credentials validation and non-interactive handling."""

    def test_missing_credentials_file_raises_filenotfound(self):
        with pytest.raises(FileNotFoundError) as exc_info:
            validate_credentials_file("non_existent_credentials_path_12345.json")
        assert "OAuth client secrets file not found" in str(exc_info.value)

    def test_non_interactive_without_token_raises_permission_error(self):
        with pytest.raises(PermissionError) as exc_info:
            get_gmail_credentials(
                credentials_path="non_existent.json",
                token_path="non_existent_token.json",
                interactive=False,
            )
        assert "No valid authorized OAuth token found" in str(exc_info.value)

    def test_scopes_is_readonly_only(self):
        assert SCOPES == ["https://www.googleapis.com/auth/gmail.readonly"]


class TestGmailClientNetworkRetries:
    """Tests for GmailClient retry logic on transient errors."""

    def test_retry_on_network_error(self):
        mock_creds = MagicMock()
        client = GmailClient(credentials=mock_creds, max_retries=3, retry_delay=0.01)

        # Mock service execution that fails once with ConnectionError then succeeds
        mock_execute = MagicMock(side_effect=[ConnectionError("Temporary socket drop"), {"emailAddress": "test@gmail.com"}])
        mock_req = MagicMock()
        mock_req.execute = mock_execute

        with patch.object(client, "_service") as mock_srv:
            mock_srv.users().getProfile.return_value = mock_req
            email = client.get_mailbox_email()
            assert email == "test@gmail.com"
            assert mock_execute.call_count == 2


class TestEmailScannerWorkflow:
    """End-to-end scanner tests with mocked Gmail API and real ML inference."""

    def test_initial_sync_without_backfill(self, repo, predictor):
        mock_client = MagicMock(spec=GmailClient)
        mock_client.get_mailbox_email.return_value = "test@gmail.com"

        # Inbox has 2 existing historical emails
        mock_client.list_messages.return_value = (
            [{"id": "hist_1"}, {"id": "hist_2"}],
            None,
        )
        mock_client.get_message.return_value = {"id": "hist_1", "internalDate": "1730000000000"}

        scanner = EmailScanner(
            gmail_client=mock_client,
            repository=repo,
            predictor=predictor,
            polling_interval=60,
            backfill_limit=0,
        )

        scanner.initialize_sync_point()

        # Verify sync point is recorded and NO historical emails were scanned
        sync_state = repo.get_sync_state("test@gmail.com")
        assert sync_state is not None
        assert sync_state["last_internal_date"] == 1730000000000
        assert repo.get_scan_count("test@gmail.com") == 0

    def test_initial_sync_with_backfill(self, repo, predictor):
        mock_client = MagicMock(spec=GmailClient)
        mock_client.get_mailbox_email.return_value = "test@gmail.com"

        msg1 = create_mock_message("bf_1", "Hello Friend", "Let's meet tomorrow for lunch.")
        msg2 = create_mock_message("bf_2", "URGENT: Verify account", "Please verify your bank credentials immediately at http://evil-login.xyz")

        mock_client.list_messages.return_value = ([{"id": "bf_1"}, {"id": "bf_2"}], None)
        mock_client.get_message.side_effect = lambda m_id, format="full": msg1 if m_id == "bf_1" else msg2

        scanner = EmailScanner(
            gmail_client=mock_client,
            repository=repo,
            predictor=predictor,
            polling_interval=60,
            backfill_limit=2,
        )

        scanner.initialize_sync_point()

        # Verify both backfilled emails were scanned and saved
        assert repo.get_scan_count("test@gmail.com") == 2
        assert repo.is_message_scanned("test@gmail.com", "bf_1") is True
        assert repo.is_message_scanned("test@gmail.com", "bf_2") is True

    def test_scan_once_detects_new_email_and_persists_classification(self, repo, predictor):
        mock_client = MagicMock(spec=GmailClient)
        mock_client.get_mailbox_email.return_value = "test@gmail.com"

        phishing_email = create_mock_message(
            "phish_new_1",
            subject="CRITICAL SECURITY ALERT: Suspicious login detected",
            body="Your account has been suspended due to unauthorized access. Click http://restore-account-secure.ru to unlock your account immediately.",
            sender="security@account-recovery.com",
            internal_date_ms=1730000050000,
        )

        mock_client.list_messages.return_value = ([{"id": "phish_new_1"}], None)
        mock_client.get_message.return_value = phishing_email

        scanned_records = []
        def on_scanned_callback(parsed, result):
            scanned_records.append((parsed, result))

        scanner = EmailScanner(
            gmail_client=mock_client,
            repository=repo,
            predictor=predictor,
            polling_interval=60,
            on_email_scanned=on_scanned_callback,
        )

        count = scanner.scan_once()
        assert count == 1
        assert len(scanned_records) == 1

        parsed, result = scanned_records[0]
        assert parsed.message_id == "phish_new_1"
        assert result["classification"] in ("Phishing", "Legitimate")
        assert 0.0 <= result["phishing_probability"] <= 1.0
        assert result["ensemble_weights"]["logistic_regression"] == 0.50
        assert result["ensemble_weights"]["lightgbm"] == 0.50
        assert result["threshold"] == 0.50

        # Verify DB storage
        assert repo.is_message_scanned("test@gmail.com", "phish_new_1") is True
        recent = repo.get_recent_scans("test@gmail.com", limit=1)
        assert len(recent) == 1
        assert recent[0]["gmail_message_id"] == "phish_new_1"
        assert recent[0]["sender"] == "security@account-recovery.com"
        assert recent[0]["body"] == "Your account has been suspended due to unauthorized access. Click http://restore-account-secure.ru to unlock your account immediately."
        assert recent[0]["classification"] == result["classification"]
        assert recent[0]["phishing_probability"] == pytest.approx(result["phishing_probability"], abs=1e-4)

    def test_duplicate_prevention_on_second_scan(self, repo, predictor):
        mock_client = MagicMock(spec=GmailClient)
        mock_client.get_mailbox_email.return_value = "test@gmail.com"

        msg = create_mock_message("msg_repeat", "Weekly Report", "Here is the summary of project progress this week.")
        mock_client.list_messages.return_value = ([{"id": "msg_repeat"}], None)
        mock_client.get_message.return_value = msg

        scanner = EmailScanner(
            gmail_client=mock_client,
            repository=repo,
            predictor=predictor,
        )

        # First scan should process 1 email
        assert scanner.scan_once() == 1
        assert repo.get_scan_count("test@gmail.com") == 1

        # Second scan with identical message ID in inbox must skip it (0 scanned)
        assert scanner.scan_once() == 0
        assert repo.get_scan_count("test@gmail.com") == 1

    def test_scanner_handles_pagination(self, repo, predictor):
        mock_client = MagicMock(spec=GmailClient)
        mock_client.get_mailbox_email.return_value = "test@gmail.com"

        # Page 1 returns msg_p1, nextPageToken='token_page_2'
        # Page 2 returns msg_p2, nextPageToken=None
        def mock_list_messages(query, max_results, page_token=None):
            if page_token is None:
                return [{"id": "msg_p1"}], "token_page_2"
            elif page_token == "token_page_2":
                return [{"id": "msg_p2"}], None
            return [], None

        mock_client.list_messages.side_effect = mock_list_messages
        mock_client.get_message.side_effect = lambda m_id, format="full": create_mock_message(
            m_id, f"Subject for {m_id}", f"Body content for {m_id} testing pagination."
        )

        scanner = EmailScanner(
            gmail_client=mock_client,
            repository=repo,
            predictor=predictor,
        )

        count = scanner.scan_once()
        assert count == 2
        assert repo.is_message_scanned("test@gmail.com", "msg_p1") is True
        assert repo.is_message_scanned("test@gmail.com", "msg_p2") is True

    def test_scanner_handles_malformed_message_safely(self, repo, predictor):
        mock_client = MagicMock(spec=GmailClient)
        mock_client.get_mailbox_email.return_value = "test@gmail.com"

        # First message is corrupted / raises exception; second message is valid
        def mock_get_message(m_id, format="full"):
            if m_id == "corrupt_msg":
                raise RuntimeError("Corrupted MIME payload from upstream")
            return create_mock_message("valid_msg", "Normal Update", "All systems operational.")

        mock_client.list_messages.return_value = ([{"id": "corrupt_msg"}, {"id": "valid_msg"}], None)
        mock_client.get_message.side_effect = mock_get_message

        scanner = EmailScanner(
            gmail_client=mock_client,
            repository=repo,
            predictor=predictor,
        )

        # Scanner should not crash; it should log the failure and process valid_msg
        count = scanner.scan_once()
        assert count == 1
        assert repo.is_message_scanned("test@gmail.com", "corrupt_msg") is False
        assert repo.is_message_scanned("test@gmail.com", "valid_msg") is True

