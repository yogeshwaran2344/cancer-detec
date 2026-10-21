"""
Dashboard Summary Schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class RecentAssessmentSummary(BaseModel):
    id: str
    date: str
    assessment_type: str
    status: str
    findings_count: int
    discordances_count: int


class DashboardMetrics(BaseModel):
    total_assessments: int = 0
    pending_verifications: int = 0
    active_reconciliations: int = 0
    last_assessment_date: Optional[str] = None


class DashboardSummaryResponse(BaseModel):
    status: str = "success"
    metrics: DashboardMetrics
    recent_assessments: List[RecentAssessmentSummary] = []
    system_notice: str = "Assessment summary ready — strictly for clinical decision support; no automated cancer likelihood calculated."
    timestamp: str
