"""
Diagnostic Scan Report Schemas
Defines request/response models for file upload, text extraction, OCR error tracking,
section segmentation, and user verification workflows.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from app.schemas.assessment import FindingItem


class PassageAnchor(BaseModel):
    id: str
    section: str
    text: str
    page: Optional[int] = 1


class ExtractionErrorItem(BaseModel):
    page: int = 1
    issue: str
    severity: str = "notice"  # notice | caution | error


class ReportUploadResponse(BaseModel):
    status: str = "success"
    report_id: str
    filename: str
    size_kb: float
    content_type: Optional[str] = None
    pages_count: int = 1
    extraction_method: str
    confidence: float
    raw_text: str
    sections: Dict[str, str] = {}
    findings: List[FindingItem] = []
    passages: List[PassageAnchor] = []
    extraction_errors: List[ExtractionErrorItem] = []
    processing_status: str = "needs_review"  # uploaded | processing | needs_review | verified | failed
    is_verified: bool = False
    message: str = "Report extracted in local privacy sandbox. Needs user verification before assessment use."
    disclaimer: str = "Verified indicates text review by user; not clinical validation."


class ReportVerificationRequest(BaseModel):
    report_id: str
    verified_findings: List[FindingItem]
    corrected_raw_text: Optional[str] = None
    corrected_sections: Optional[Dict[str, str]] = None
    notes: Optional[str] = None


class ReportVerificationResponse(BaseModel):
    status: str = "success"
    report_id: str
    processing_status: str = "verified"
    is_verified: bool = True
    verified_findings_count: int
    verified_at: str
    message: str = "Report extraction confirmed by user. Verified text ready for assessment reconciliation."
    disclaimer: str = "Verified indicates text review by user; not clinical validation."
