"""Scanner monitoring status API routes."""

import os
from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.config import (
    GMAIL_CREDENTIALS_PATH,
    GMAIL_TOKEN_PATH,
    POLLING_INTERVAL_SECONDS,
)
from backend.database_service import DatabaseService
from backend.schemas import ScannerStatus

router = APIRouter(prefix="/api/monitor", tags=["Monitor"])
db_service = DatabaseService()


@router.get("/status", response_model=ScannerStatus)
def get_monitor_status(current_user: str = Depends(get_current_user)):
    """Retrieve operational health, sync checkpoint, and connectivity of the Gmail scanner."""
    sync_state = db_service.get_monitor_state()

    cred_exists = os.path.exists(GMAIL_CREDENTIALS_PATH)
    token_exists = os.path.exists(GMAIL_TOKEN_PATH)

    # Validate token validity without exposing contents
    is_authorized = False
    if token_exists:
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH)
            is_authorized = bool(creds and (creds.valid or creds.refresh_token))
        except Exception:
            is_authorized = False

    return ScannerStatus(
        mailbox=sync_state.get("mailbox"),
        oauth_authorized=is_authorized,
        sync_status=sync_state.get("status", "IDLE"),
        last_history_id=sync_state.get("last_history_id"),
        last_internal_date=sync_state.get("last_internal_date"),
        last_sync_at=sync_state.get("last_sync_at"),
        polling_interval_seconds=POLLING_INTERVAL_SECONDS,
        credentials_file_present=cred_exists,
        token_file_present=token_exists,
        last_error=None,
    )

