"""Gmail API integration package for ZanderEtAlFishing."""

from gmail_integration.auth import get_gmail_credentials, validate_credentials_file, SCOPES
from gmail_integration.email_parser import ParsedEmail, parse_gmail_message, combine_subject_and_body
from gmail_integration.gmail_client import GmailClient
from gmail_integration.scanner import EmailScanner

__all__ = [
    "get_gmail_credentials",
    "validate_credentials_file",
    "SCOPES",
    "ParsedEmail",
    "parse_gmail_message",
    "combine_subject_and_body",
    "GmailClient",
    "EmailScanner",
]

