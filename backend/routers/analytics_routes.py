"""Analytics and metrics API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, Query

from backend.auth import get_current_user
from backend.database_service import DatabaseService
from backend.schemas import AnalyticsOverview

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])
db_service = DatabaseService()


@router.get("/overview", response_model=AnalyticsOverview)
def get_analytics_overview(
    start_date: Optional[str] = Query(None, description="Start date ISO string"),
    end_date: Optional[str] = Query(None, description="End date ISO string"),
    current_user: str = Depends(get_current_user),
):
    """Retrieve operational time-series data and verified research evaluation benchmarks."""
    data = db_service.get_analytics_overview(start_date=start_date, end_date=end_date)
    return AnalyticsOverview(**data)

