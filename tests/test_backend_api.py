"""Comprehensive tests for ZanderEtAlFishing Phase 3 FastAPI Backend."""

import os
import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.config import ADMIN_PASSWORD, ADMIN_USERNAME
from database.connection import init_db
from database.repository import ScanRepository


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Authenticate and return valid authorization bearer headers."""
    resp = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health_check(client):
    """Test public health check endpoint."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert "service" in data
    assert "timestamp" in data
    assert data["database_connected"] is True


def test_auth_failure(client):
    """Test login failure with incorrect credentials."""
    resp = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "WrongPassword123!"},
    )
    assert resp.status_code == 401
    assert "detail" in resp.json()


def test_auth_success(client):
    """Test successful login returns valid JWT token."""
    resp = client.post(
        "/api/auth/login",
        json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["username"] == ADMIN_USERNAME


def test_unauthorized_access(client):
    """Test protected endpoints reject unauthenticated requests with 401."""
    endpoints = [
        "/api/auth/me",
        "/api/dashboard/summary",
        "/api/emails",
        "/api/emails/1",
        "/api/analytics/overview",
        "/api/monitor/status",
        "/api/model/info",
    ]
    for ep in endpoints:
        resp = client.get(ep)
        assert resp.status_code == 401, f"Expected 401 for {ep}, got {resp.status_code}"


def test_dashboard_summary(client, auth_headers):
    """Test dashboard summary endpoint returns actual database statistics."""
    resp = client.get("/api/dashboard/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_scanned" in data
    assert "total_phishing" in data
    assert "total_legitimate" in data
    assert "average_latency_ms" in data
    assert "recent_scans" in data
    assert "recent_phishing_warnings" in data
    assert data["total_scanned"] == data["total_phishing"] + data["total_legitimate"]


def test_email_listing_and_pagination(client, auth_headers):
    """Test listing scanned emails with pagination."""
    resp = client.get("/api/emails?page=1&page_size=10", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) <= 10


def test_email_filtering_by_classification(client, auth_headers):
    """Test filtering emails by Phishing and Legitimate classification."""
    # Phishing filter
    resp_phish = client.get("/api/emails?classification=Phishing", headers=auth_headers)
    assert resp_phish.status_code == 200
    items_phish = resp_phish.json()["items"]
    for item in items_phish:
        assert item["classification"] == "Phishing"

    # Legitimate filter
    resp_legit = client.get("/api/emails?classification=Legitimate", headers=auth_headers)
    assert resp_legit.status_code == 200
    items_legit = resp_legit.json()["items"]
    for item in items_legit:
        assert item["classification"] == "Legitimate"


def test_email_search(client, auth_headers):
    """Test searching emails by keyword."""
    resp = client.get("/api/emails?search=YouTube", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    for item in data["items"]:
        match = "youtube" in (item["subject"] or "").lower() or "youtube" in (item["sender"] or "").lower()
        assert match


def test_email_detail(client, auth_headers):
    """Test retrieving email scan detail by ID."""
    # Get first email ID from list
    list_resp = client.get("/api/emails?page=1&page_size=1", headers=auth_headers)
    items = list_resp.json()["items"]
    if items:
        target_id = items[0]["id"]
        detail_resp = client.get(f"/api/emails/{target_id}", headers=auth_headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == target_id
        assert "phishing_probability" in detail
        assert "logistic_regression_probability" in detail
        assert "lightgbm_probability" in detail
        assert "body" in detail
        assert "ensemble_weights" in detail
        assert detail["ensemble_weights"]["logistic_regression"] == 0.50
        assert detail["ensemble_weights"]["lightgbm"] == 0.50


def test_email_detail_not_found(client, auth_headers):
    """Test 404 response for non-existent email ID."""
    resp = client.get("/api/emails/99999999", headers=auth_headers)
    assert resp.status_code == 404


def test_analytics_overview(client, auth_headers):
    """Test analytics overview contains time-series and research benchmark."""
    resp = client.get("/api/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "time_series" in data
    assert "distribution" in data
    assert "latency_trends" in data
    assert "research_benchmark" in data
    assert data["research_benchmark"]["roc_auc"] > 0.99
    assert len(data["research_benchmark"]["metrics"]) > 0


def test_monitor_status(client, auth_headers):
    """Test monitor status reports connectivity without leaking secrets."""
    resp = client.get("/api/monitor/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "sync_status" in data
    assert "polling_interval_seconds" in data
    assert "credentials_file_present" in data
    assert "token_file_present" in data
    # Ensure no secrets leaked
    assert "client_secret" not in data
    assert "token" not in data or isinstance(data.get("token"), bool)


def test_model_info(client, auth_headers):
    """Test model info endpoint returns feature dimensions and ensemble weights."""
    resp = client.get("/api/model/info", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["system_name"] == "ZanderEtAlFishing"
    assert data["threshold"] == 0.50
    assert data["high_confidence_threshold"] == 0.70
    assert data["ensemble_weights"]["logistic_regression"] == 0.50
    assert data["ensemble_weights"]["lightgbm"] == 0.50
    assert data["models_loaded"]["logistic_regression"] is True
    assert data["models_loaded"]["lightgbm"] is True


def test_dashboard_summary_suspicious_tier(client, auth_headers):
    """Test dashboard summary includes total_suspicious field."""
    resp = client.get("/api/dashboard/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_suspicious" in data
    assert isinstance(data["total_suspicious"], int)
    assert data["total_suspicious"] >= 0


def test_email_detail_tier_and_thresholds(client, auth_headers):
    """Test email detail includes risk_tier and dual thresholds."""
    list_resp = client.get("/api/emails?page=1&page_size=1", headers=auth_headers)
    items = list_resp.json()["items"]
    if items:
        target_id = items[0]["id"]
        detail_resp = client.get(f"/api/emails/{target_id}", headers=auth_headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert "risk_tier" in detail
        assert detail["risk_tier"] in ("Legitimate", "Suspicious", "High-Confidence Phishing", None)
        assert detail["threshold"] == 0.50
        assert detail["high_confidence_threshold"] == 0.70
        assert "spf_pass" in detail
        assert "dkim_pass" in detail
        assert "dmarc_pass" in detail


def test_email_filtering_by_suspicious_and_high_confidence(client, auth_headers):
    """Test filtering by Suspicious and High-Confidence Phishing tiers."""
    # Filter by Suspicious
    resp_susp = client.get("/api/emails?classification=Suspicious", headers=auth_headers)
    assert resp_susp.status_code == 200
    items_susp = resp_susp.json()["items"]
    for item in items_susp:
        assert item["risk_tier"] == "Suspicious"

    # Filter by High-Confidence Phishing
    resp_high = client.get("/api/emails?classification=High-Confidence%20Phishing", headers=auth_headers)
    assert resp_high.status_code == 200
    items_high = resp_high.json()["items"]
    for item in items_high:
        assert item["risk_tier"] == "High-Confidence Phishing"


def test_empty_database_behavior(tmp_path):
    """Test that database service handles an empty database gracefully."""
    empty_db_path = str(tmp_path / "empty.db")
    from backend.database_service import DatabaseService
    empty_service = DatabaseService(db_path=empty_db_path)

    stats = empty_service.get_summary_stats()
    assert stats["total_scanned"] == 0
    assert stats["total_phishing"] == 0
    assert stats["total_legitimate"] == 0
    assert stats["average_latency_ms"] == 0.0
    assert stats["recent_scans"] == []
    assert stats["recent_phishing_warnings"] == []

    items, total, total_pages = empty_service.get_emails()
    assert items == []
    assert total == 0
    assert total_pages == 1


def test_spa_index_served(client):
    """Test that non-API paths serve the frontend index.html."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "ZanderEtAlFishing" in resp.text

