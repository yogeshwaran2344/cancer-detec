"""
Dashboard Summary Endpoint
Returns consolidated metrics and recent clinical assessments for the frontend workspace.
"""

from fastapi import APIRouter, Depends
from typing import Optional
import datetime
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardMetrics,
    RecentAssessmentSummary
)
from app.core.auth import get_optional_authenticated_user, AuthenticatedUser
from app.db.repository import list_assessment_records
from app.db.database import get_db

router = APIRouter()


@router.get("", response_model=DashboardSummaryResponse)
@router.get("/", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: Optional[AuthenticatedUser] = Depends(get_optional_authenticated_user)
) -> DashboardSummaryResponse:
    """Consolidates key metrics and recent assessment activity from SQLite for the caller's workspace."""
    eff_user_id = current_user.user_id if current_user else None
    total_count, assessments_list = list_assessment_records(user_id=eff_user_id, limit=10)
    recent_items = []

    for item in assessments_list[:5]:
        recent_items.append(
            RecentAssessmentSummary(
                id=item["id"],
                date=item["date"],
                assessment_type=item.get("type", "Clinical Assessment"),
                status=item.get("status", "Assessment summary ready"),
                findings_count=item.get("findings_count", 0),
                discordances_count=1 if item.get("report_linked") else 0
            )
        )

    last_date = recent_items[0].date if recent_items else None

    # Count pending verifications in reports table
    pending_verifications = 0
    with get_db() as conn:
        row = conn.execute("SELECT COUNT(*) FROM reports WHERE is_verified = 0;").fetchone()
        if row:
            pending_verifications = row[0]

    metrics = DashboardMetrics(
        total_assessments=total_count,
        pending_verifications=pending_verifications,
        active_reconciliations=len([a for a in assessments_list if a.get("report_linked")]),
        last_assessment_date=last_date
    )

    return DashboardSummaryResponse(
        status="success",
        metrics=metrics,
        recent_assessments=recent_items,
        system_notice="Assessment summary ready — strictly for clinical decision support; no automated cancer likelihood calculated.",
        timestamp=datetime.datetime.now().isoformat()
    )
