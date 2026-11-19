"""OAuth 2.0 authentication module for Google Gmail API."""

import os
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# STRICT: Read-only scope as required by Phase 2 specification
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

DEFAULT_CREDENTIALS_PATH = os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials/credentials.json")
DEFAULT_TOKEN_PATH = os.environ.get("GMAIL_TOKEN_PATH", "credentials/token.json")


def validate_credentials_file(credentials_path: str) -> None:
    """Validate that the OAuth client secrets file exists and is readable."""
    if not os.path.exists(credentials_path):
        raise FileNotFoundError(
            f"OAuth client secrets file not found at: {credentials_path}\n"
            "Please ensure you have downloaded your Google OAuth 2.0 Desktop Application "
            f"credentials JSON and placed it at '{credentials_path}'."
        )


def get_gmail_credentials(
    credentials_path: Optional[str] = None,
    token_path: Optional[str] = None,
    interactive: bool = True,
) -> Credentials:
    """Authenticate and return valid Google OAuth2 Credentials for Gmail read-only access.
    
    1. Checks for an existing saved authorization token.
    2. Refreshes the token if expired.
    3. If no valid token exists and interactive is True, launches the local browser flow.
    4. Saves the refreshed or newly generated token securely in token_path.
    
    Never prints or reveals credentials or token content.
    """
    cred_file = credentials_path or os.environ.get("GMAIL_CREDENTIALS_PATH", DEFAULT_CREDENTIALS_PATH)
    tok_file = token_path or os.environ.get("GMAIL_TOKEN_PATH", DEFAULT_TOKEN_PATH)

    # Ensure parent directory for token file exists
    tok_dir = os.path.dirname(tok_file)
    if tok_dir:
        os.makedirs(tok_dir, exist_ok=True)

    creds: Optional[Credentials] = None

    # Load existing token if present
    if os.path.exists(tok_file):
        try:
            creds = Credentials.from_authorized_user_file(tok_file, SCOPES)
        except Exception:
            # Token corrupted or invalid
            creds = None

    # Check validity or refresh if expired
    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Save refreshed token
            with open(tok_file, "w", encoding="utf-8") as token_out:
                token_out.write(creds.to_json())
            return creds
        except Exception:
            # Refresh failed (e.g. revoked token), fall back to re-authorization if interactive
            creds = None

    # No valid credentials; execute local browser-based OAuth flow
    if not interactive:
        raise PermissionError(
            f"No valid authorized OAuth token found at '{tok_file}' and interactive flow is disabled."
        )

    validate_credentials_file(cred_file)

    flow = InstalledAppFlow.from_client_secrets_file(cred_file, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save newly authorized token
    with open(tok_file, "w", encoding="utf-8") as token_out:
        token_out.write(creds.to_json())

    return creds

