"""Pydantic data validation schemas for ZanderEtAlFishing Dashboard."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# Authentication schemas
class LoginRequest(BaseModel):
    username: str = Field(..., description="Administrator username")
    password: str = Field(..., description="Administrator password")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    username: str


class UserProfile(BaseModel):
    username: str
    role: str
    authenticated: bool


# Email scan schemas
class EmailScanItem(BaseModel):
    id: int
    mailbox: str
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    received_at: str
    classification: str
    risk_tier: Optional[str] = None
    phishing_probability: float
    logistic_regression_probability: float
    lightgbm_probability: float
    inference_time_ms: float
    scanned_at: str
    model_version: str
    spf_pass: Optional[bool] = None
    dkim_pass: Optional[bool] = None
    dmarc_pass: Optional[bool] = None


class EmailListResponse(BaseModel):
    items: List[EmailScanItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class EnsembleWeights(BaseModel):
    logistic_regression: float = 0.50
    lightgbm: float = 0.50


class EmailScanDetail(BaseModel):
    id: int
    mailbox: str
    gmail_message_id: str
    gmail_thread_id: Optional[str] = None
    sender: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    received_at: str
    scanned_at: str
    classification: str
    risk_tier: Optional[str] = None
    phishing_probability: float
    logistic_regression_probability: float
    lightgbm_probability: float
    inference_time_ms: float
    model_version: str
    threshold: float = 0.50
    high_confidence_threshold: float = 0.70
    ensemble_weights: EnsembleWeights = EnsembleWeights()
    spf_pass: Optional[bool] = None
    dkim_pass: Optional[bool] = None
    dmarc_pass: Optional[bool] = None
    methodology: Dict[str, Any] = Field(
        default_factory=lambda: {
            "fusion_technique": "Multi-Granularity Feature Fusion",
            "features": {
                "word_tfidf": "10,000 features (n-grams 1-2)",
                "char_tfidf": "5,000 features (n-grams 3-5)",
                "stylometrics": "9 features (scaled with StandardScaler)",
            },
            "classifiers": "50% Logistic Regression (C=5.0) + 50% LightGBM (200 trees)",
        }
    )


# Dashboard Summary schemas
class DashboardSummary(BaseModel):
    total_scanned: int
    total_phishing: int
    total_legitimate: int
    total_suspicious: int = 0
    phishing_ratio_percent: float
    average_latency_ms: float
    latest_scan_at: Optional[str] = None
    mailbox: Optional[str] = None
    scanner_status: str
    recent_phishing_warnings: List[EmailScanItem]
    recent_scans: List[EmailScanItem]


# Analytics schemas
class TimeSeriesPoint(BaseModel):
    date: str
    total_scanned: int
    phishing: int
    legitimate: int
    average_latency_ms: float


class ClassificationDistribution(BaseModel):
    phishing: int
    legitimate: int
    phishing_percentage: float
    legitimate_percentage: float


class ResearchMetricItem(BaseModel):
    metric: str
    baseline_replication: str
    proposed_hybrid: str
    delta: str


class ResearchBenchmark(BaseModel):
    title: str = "Thesis Research Model Performance Evaluation"
    dataset: str = "Combined Benchmarked Dataset (N = 61,000+ emails)"
    metrics: List[ResearchMetricItem]
    confusion_matrix: Dict[str, int]
    roc_auc: float
    avg_precision: float
    latency_ms: float
    note: str = (
        "Evaluation metrics are measured on labeled held-out test data during experimental research, "
        "distinct from operational Gmail production monitoring counts."
    )


class AnalyticsOverview(BaseModel):
    time_series: List[TimeSeriesPoint]
    distribution: ClassificationDistribution
    latency_trends: List[Dict[str, Any]]
    research_benchmark: ResearchBenchmark


# Scanner and Model status schemas
class ScannerStatus(BaseModel):
    mailbox: Optional[str]
    oauth_authorized: bool
    sync_status: str
    last_history_id: Optional[str]
    last_internal_date: Optional[int]
    last_sync_at: Optional[str]
    polling_interval_seconds: int
    credentials_file_present: bool
    token_file_present: bool
    last_error: Optional[str] = None


class ModelInfo(BaseModel):
    system_name: str
    model_version: str
    threshold: float
    high_confidence_threshold: float = 0.70
    ensemble_weights: EnsembleWeights
    models_loaded: Dict[str, bool]
    architecture: Dict[str, Any]

