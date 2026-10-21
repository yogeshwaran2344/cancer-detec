"""
PathoGuard-AI API v1 Router Aggregator
Combines versioned sub-routers for health, dashboard, assessments, and reports.
"""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    dashboard,
    assessments,
    reports,
    report_understanding,
    evaluations,
    evidence_integrity,
    auth
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Security"])
api_v1_router.include_router(health.router, prefix="/health", tags=["Health"])
api_v1_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_v1_router.include_router(assessments.router, prefix="/assessments", tags=["Assessments"])
api_v1_router.include_router(report_understanding.router, prefix="/reports", tags=["AI Report Understanding"])
api_v1_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_v1_router.include_router(evaluations.router, prefix="/evaluations", tags=["AI Evaluation & Benchmarking"])
api_v1_router.include_router(evidence_integrity.router, tags=["Evidence Integrity & Core Innovation"])
