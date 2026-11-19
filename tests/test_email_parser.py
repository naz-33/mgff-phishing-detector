"""Unit tests for Gmail message MIME parsing and email extraction."""

import base64
import pytest
from gmail_integration.email_parser import (
    combine_subject_and_body,
    decode_base64url,
    extract_body_parts,
    html_to_plain_text,
    is_attachment_part,
    parse_gmail_message,
    parse_gmail_timestamp,
)


def b64url_encode(text: str) -> str:
    """Helper to encode string into URL-safe Base64 without padding."""
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("utf-8").rstrip("=")


class TestBase64URLDecoding:
    def test_decode_standard(self):
        original = "Hello World, this is a test email!"
        encoded = b64url_encode(original)
        assert decode_base64url(encoded) == original

    def test_decode_unicode_characters(self):
        original = "Attention: Votre compte a été suspendu! 日本語 & €uro"
        encoded = b64url_encode(original)
        assert decode_base64url(encoded) == original

    def test_decode_empty_and_invalid(self):
        assert decode_base64url("") == ""


class TestHtmlToPlainText:
    def test_html_stripping_and_formatting(self):
        html = """
        <html>
            <head><style>p { color: red; }</style></head>
            <body>
                <h1>Security Alert</h1>
                <p>Please click <a href="https://evil.com">here</a> to verify.</p>
                <script>alert('bad');</script>
            </body>
        </html>
        """
        text = html_to_plain_text(html)
        assert "Security Alert" in text
        assert "Please click here to verify." in text
        assert "color: red" not in text
        assert "alert('bad')" not in text

    def test_empty_html(self):
        assert html_to_plain_text("") == ""
        assert html_to_plain_text("   ") == ""


class TestSubjectBodyCombination:
    def test_both_present(self):
        assert combine_subject_and_body("Test Subject", "Test Body") == "Test Subject\n\nTest Body"

    def test_subject_only(self):
        assert combine_subject_and_body("Test Subject", "") == "Test Subject"

    def test_body_only(self):
        assert combine_subject_and_body("", "Test Body") == "Test Body"

    def test_neither_present(self):
        assert combine_subject_and_body("", "") == "Empty email content"


class TestGmailMessageParsing:
    def test_plain_text_message(self):
        raw_msg = {
            "id": "1894a7e3b8a10",
            "threadId": "1894a7e3b8a10",
            "internalDate": "1730275200000",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "Subject", "value": "Meeting tomorrow"},
                    {"name": "From", "value": "Alice <alice@example.com>"},
                    {"name": "Date", "value": "Wed, 30 Oct 2026 08:00:00 +0000"},
                ],
                "body": {
                    "data": b64url_encode("Hi Team, reminder for the project standup tomorrow morning.")
                },
            },
        }

        parsed = parse_gmail_message(raw_msg)
        assert parsed.message_id == "1894a7e3b8a10"
        assert parsed.thread_id == "1894a7e3b8a10"
        assert parsed.sender == "Alice <alice@example.com>"
        assert parsed.subject == "Meeting tomorrow"
        assert parsed.internal_date_ms == 1730275200000
        assert "reminder for the project standup" in parsed.body
        assert parsed.content_type_used == "text/plain"
        assert "Meeting tomorrow\n\nHi Team, reminder" in parsed.combined_text

    def test_html_only_message(self):
        raw_msg = {
            "id": "html_001",
            "threadId": "thread_html_001",
            "internalDate": "1730275200000",
            "payload": {
                "mimeType": "text/html",
                "headers": [
                    {"name": "Subject", "value": "Account Notice"},
                    {"name": "From", "value": "bank@secure-login.com"},
                ],
                "body": {
                    "data": b64url_encode("<p>Your card has been locked. <b>Act now!</b></p>")
                },
            },
        }

        parsed = parse_gmail_message(raw_msg)
        assert parsed.content_type_used == "text/html"
        assert "Your card has been locked." in parsed.body
        assert "Act now!" in parsed.body

    def test_multipart_prefers_plain_text(self):
        raw_msg = {
            "id": "multi_001",
            "threadId": "thread_multi_001",
            "internalDate": "1730275200000",
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "Subject", "value": "Newsletter"},
                    {"name": "From", "value": "news@example.com"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": b64url_encode("Plain version of newsletter")},
                    },
                    {
                        "mimeType": "text/html",
                        "body": {"data": b64url_encode("<p>HTML version of newsletter</p>")},
                    },
                ],
            },
        }

        parsed = parse_gmail_message(raw_msg)
        assert parsed.content_type_used == "text/plain"
        assert parsed.body == "Plain version of newsletter"

    def test_multipart_ignores_attachments(self):
        raw_msg = {
            "id": "attach_001",
            "threadId": "thread_attach_001",
            "internalDate": "1730275200000",
            "payload": {
                "mimeType": "multipart/mixed",
                "headers": [
                    {"name": "Subject", "value": "Invoice with PDF"},
                    {"name": "From", "value": "billing@example.com"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {"data": b64url_encode("Please see the attached invoice.")},
                    },
                    {
                        "mimeType": "application/pdf",
                        "filename": "invoice_october.pdf",
                        "headers": [
                            {"name": "Content-Disposition", "value": 'attachment; filename="invoice_october.pdf"'}
                        ],
                        "body": {"data": b64url_encode("PDF BINARY DATA SHOULD BE IGNORED")},
                    },
                ],
            },
        }

        parsed = parse_gmail_message(raw_msg)
        assert parsed.content_type_used == "text/plain"
        assert parsed.body == "Please see the attached invoice."
        assert "PDF BINARY DATA" not in parsed.body


class TestAuthenticationResultsParsing:
    """Tests for SPF, DKIM, and DMARC gateway header extraction."""

    def test_all_auth_checks_pass(self):
        auth_header = (
            "mx.google.com; "
            "dkim=pass header.i=@facebookmail.com header.s=s1024-2013-q3; "
            "spf=pass (google.com: domain of notification+xyz@facebookmail.com designates 66.220.144.137 as permitted sender) smtp.mailfrom=notification+xyz@facebookmail.com; "
            "dmarc=pass (p=REJECT sp=REJECT dis=NONE) header.from=facebookmail.com"
        )
        raw_msg = {
            "id": "auth_001",
            "threadId": "thread_auth_001",
            "internalDate": "1730275200000",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "Subject", "value": "Friend Request"},
                    {"name": "From", "value": "Facebook <notification+xyz@facebookmail.com>"},
                    {"name": "Authentication-Results", "value": auth_header},
                ],
                "body": {"data": b64url_encode("John Doe wants to be friends on Facebook.")},
            },
        }

        parsed = parse_gmail_message(raw_msg)
        assert parsed.spf_pass is True
        assert parsed.dkim_pass is True
        assert parsed.dmarc_pass is True

    def test_auth_checks_failures(self):
        auth_header = (
            "mx.google.com; "
            "dkim=fail header.i=@spoofed.com; "
            "spf=softfail (google.com: domain of admin@spoofed.com does not designate IP) smtp.mailfrom=admin@spoofed.com; "
            "dmarc=fail action=none header.from=spoofed.com"
        )
        raw_msg = {
            "id": "auth_002",
            "threadId": "thread_auth_002",
            "internalDate": "1730275200000",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "Subject", "value": "Urgent update"},
                    {"name": "From", "value": "Spoofed <admin@spoofed.com>"},
                    {"name": "Authentication-Results", "value": auth_header},
                ],
                "body": {"data": b64url_encode("Click to verify account.")},
            },
        }

        parsed = parse_gmail_message(raw_msg)
        assert parsed.spf_pass is False
        assert parsed.dkim_pass is False
        assert parsed.dmarc_pass is False

    def test_no_auth_header_defaults_to_none(self):
        raw_msg = {
            "id": "auth_003",
            "threadId": "thread_auth_003",
            "internalDate": "1730275200000",
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "Subject", "value": "Hello"},
                    {"name": "From", "value": "friend@example.com"},
                ],
                "body": {"data": b64url_encode("Hey there!")},
            },
        }

        parsed = parse_gmail_message(raw_msg)
        assert parsed.spf_pass is None
        assert parsed.dkim_pass is None
        assert parsed.dmarc_pass is None

