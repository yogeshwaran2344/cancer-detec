"""
PathoGuard-AI API Endpoints Router (Legacy & General Aliases)
Maintains backward compatibility with earlier iterations while forwarding to v1 structures.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import datetime
from app.services.document_parser import extract_report_document, extract_text_from_file
from app.api.v1.endpoints.reports import upload_scan_report
from app.schemas.assessment import AssessmentCreate

router = APIRouter()


@router.get("/health")
def api_health():
    """Healthcheck endpoint for dashboard connection verification"""
    return {
        "status": "healthy",
        "service": "PathoGuard-Backend",
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().isoformat()
    }


@router.post("/reports/parse")
async def parse_scan_report_legacy(file: UploadFile = File(...)):
    """Receives, validates, and extracts text from uploaded diagnostic scan reports"""
    res = await upload_scan_report(file=file)
    return res.model_dump()


@router.post("/symptoms/intake")
def receive_symptoms_legacy(payload: AssessmentCreate):
    """Receives and validates patient symptom responses"""
    return {
        "status": "success",
        "logged_symptoms_count": len(payload.primary_symptoms),
        "trajectory": payload.trajectory,
        "timestamp": datetime.datetime.now().isoformat()
    }
