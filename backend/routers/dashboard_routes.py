"""Dashboard summary API routes."""

from fastapi import APIRouter, Depends

from backend.auth import get_current_user
from backend.database_service import DatabaseService
from backend.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
db_service = DatabaseService()


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary(current_user: str = Depends(get_current_user)):
    """Retrieve operational metrics and recent alerts from the Phase 2 database."""
    stats = db_service.get_summary_stats()
    return DashboardSummary(**stats)

