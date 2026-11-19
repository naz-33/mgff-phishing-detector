"""Monitored emails API routes."""

import json
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.auth import get_current_user
from backend.config import BASE_DIR
from backend.database_service import DatabaseService
from backend.schemas import EmailListResponse, EmailScanDetail, EmailScanItem, EnsembleWeights

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/emails", tags=["Emails"])
db_service = DatabaseService()


def _fetch_and_cache_email_body(email_id: int, gmail_message_id: str) -> Optional[str]:
    """Attempt on-demand retrieval of email body from Gmail API and cache in SQLite."""
    if not gmail_message_id:
        return None
    try:
        from gmail_integration.auth import get_gmail_credentials
        from gmail_integration.gmail_client import GmailClient
        from gmail_integration.email_parser import parse_gmail_message

        creds = get_gmail_credentials(interactive=False)
        client = GmailClient(credentials=creds)
        raw_msg = client.get_message(gmail_message_id, format="full")
        parsed = parse_gmail_message(raw_msg)
        body = parsed.body or parsed.combined_text
        if body:
            db_service.update_email_body(email_id, body)
            logger.info("Successfully fetched and cached body for scan ID %s from Gmail", email_id)
            return body
    except Exception as e:
        logger.debug(
            "On-demand Gmail fetch skipped or failed for ID %s (msg %s): %s",
            email_id,
            gmail_message_id,
            e,
        )
    return None

def _get_inference_thresholds():
    config_path = BASE_DIR / "models" / "inference_config.json"
    threshold = 0.50
    high_confidence_threshold = 0.70
    w_lr = 0.50
    w_lgb = 0.50
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                threshold = float(cfg.get("threshold", threshold))
                high_confidence_threshold = float(cfg.get("high_confidence_threshold", high_confidence_threshold))
                w_lr = float(cfg.get("ensemble_weight_lr", w_lr))
                w_lgb = float(cfg.get("ensemble_weight_lgbm", w_lgb))
        except Exception:
            pass
    return threshold, high_confidence_threshold, w_lr, w_lgb


@router.get("", response_model=EmailListResponse)
def list_emails(
    page: int = Query(1, ge=1, description="Page number (starts at 1)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term in subject or sender"),
    classification: Optional[str] = Query(None, description="Filter by classification (Phishing/Legitimate)"),
    sort_by: str = Query("received_at", description="Field to sort by"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    current_user: str = Depends(get_current_user),
):
    """Retrieve paginated and filtered list of monitored email scan records."""
    items_data, total, total_pages = db_service.get_emails(
        page=page,
        page_size=page_size,
        search=search,
        classification=classification,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    items = [EmailScanItem(**item) for item in items_data]
    return EmailListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{email_id}", response_model=EmailScanDetail)
def get_email_detail(
    email_id: int,
    current_user: str = Depends(get_current_user),
):
    """Retrieve detailed detection breakdown for a specific scanned email record."""
    record = db_service.get_email_by_id(email_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email scan record with ID {email_id} not found",
        )

    threshold, high_confidence_threshold, w_lr, w_lgb = _get_inference_thresholds()

    # On-demand email body retrieval from Gmail if missing in DB
    body = record.get("body")
    if not body and record.get("gmail_message_id"):
        body = _fetch_and_cache_email_body(record["id"], record["gmail_message_id"])

    return EmailScanDetail(
        id=record["id"],
        mailbox=record["mailbox"],
        gmail_message_id=record["gmail_message_id"],
        gmail_thread_id=record.get("gmail_thread_id"),
        sender=record.get("sender"),
        subject=record.get("subject"),
        body=body,
        received_at=record["received_at"],
        scanned_at=record["scanned_at"],
        classification=record["classification"],
        risk_tier=record.get("risk_tier"),
        phishing_probability=record["phishing_probability"],
        logistic_regression_probability=record["logistic_regression_probability"],
        lightgbm_probability=record["lightgbm_probability"],
        inference_time_ms=record["inference_time_ms"],
        model_version=record["model_version"],
        threshold=threshold,
        high_confidence_threshold=high_confidence_threshold,
        ensemble_weights=EnsembleWeights(
            logistic_regression=w_lr,
            lightgbm=w_lgb,
        ),
        spf_pass=bool(record["spf_pass"]) if record.get("spf_pass") is not None else None,
        dkim_pass=bool(record["dkim_pass"]) if record.get("dkim_pass") is not None else None,
        dmarc_pass=bool(record["dmarc_pass"]) if record.get("dmarc_pass") is not None else None,
    )


@router.post("/{email_id}/fetch-body", response_model=EmailScanDetail)
def fetch_email_body_on_demand(
    email_id: int,
    current_user: str = Depends(get_current_user),
):
    """Explicitly trigger on-demand retrieval of email body from Gmail API."""
    record = db_service.get_email_by_id(email_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Email scan record with ID {email_id} not found",
        )

    msg_id = record.get("gmail_message_id")
    if not msg_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Record has no Gmail message ID",
        )

    # Attempt fetch and cache
    body = _fetch_and_cache_email_body(record["id"], msg_id)
    if not body and not record.get("body"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not retrieve email body from Gmail (it may have been deleted from your inbox or Gmail rate limit reached).",
        )

    return get_email_detail(email_id=email_id, current_user=current_user)

