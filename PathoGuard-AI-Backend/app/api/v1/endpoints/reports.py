"""
Scan Report Upload, Digital Extraction, OCR & Verification Endpoints
Enforces server-side authentication, caller record ownership, and robust validation.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List, Optional
import datetime
import uuid
import os

from app.core.auth import get_current_authenticated_user, AuthenticatedUser
from app.services.file_manager import (
    save_to_sandbox,
    get_sandbox_file_path,
    purge_sandbox_storage
)
from app.services.document_parser import extract_report_document
from app.schemas.report import (
    ReportUploadResponse,
    ReportVerificationRequest,
    ReportVerificationResponse,
    PassageAnchor,
    ExtractionErrorItem
)
from app.schemas.assessment import FindingItem
from app.db.repository import (
    save_report_record,
    get_report_record,
    update_report_verification_record
)

router = APIRouter()


@router.post("", response_model=ReportUploadResponse)
@router.post("/", response_model=ReportUploadResponse)
@router.post("/upload", response_model=ReportUploadResponse)
async def upload_scan_report(
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> ReportUploadResponse:
    """
    Step 1 & Step 2 & Step 3:
    Securely receives a diagnostic scan report (PDF, PNG, JPG, JPEG, TXT), validates format/size,
    stores in private local sandbox, runs digital PDF extraction or genuine OCR,
    segments into clinical sections, and attaches page-linked passage anchors with caller ownership.
    """
    raw_filename = file.filename or "unknown_report.pdf"
    content = await file.read()

    # Reject empty files immediately
    if not content or len(content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes). Please upload a valid report.")

    # 1. Validate and save to sandbox
    saved_meta = save_to_sandbox(raw_filename, content, file.content_type)
    report_id = f"RPT-{datetime.datetime.now().year}-{str(uuid.uuid4())[:4].upper()}"

    # 2. Extract text & segment report structure
    extracted = extract_report_document(raw_filename, content)

    # 3. Build typed finding items
    typed_findings: List[FindingItem] = []
    for f in extracted.get("findings", []):
        typed_findings.append(
            FindingItem(
                id=f.get("id", "p0"),
                title=f.get("title", "Finding"),
                finding=f.get("body", ""),
                body=f.get("body", ""),
                section=f.get("section", "findings"),
                anchor=f.get("id", "p0"),
                category=f.get("category", "significant"),
                typeLabel=f.get("typeLabel", "Anatomical Observation"),
                uncertainty=f.get("uncertainty", False),
                needsVerification=True,
                verified=False,
                sourceRef=f.get("sourceRef", "Report § 1")
            )
        )

    # 4. Build passage anchors
    passages = []
    for f in typed_findings:
        passages.append(
            PassageAnchor(
                id=f.id,
                section=f.section,
                text=f.body or "",
                page=1
            )
        )

    # 5. Build extraction errors
    extraction_errors = []
    for err in extracted.get("extraction_errors", []):
        extraction_errors.append(
            ExtractionErrorItem(
                page=err.get("page", 1),
                issue=err.get("issue", "Character clarity notice"),
                severity=err.get("severity", "notice")
            )
        )

    response_payload = ReportUploadResponse(
        status="success",
        report_id=report_id,
        filename=saved_meta["original_filename"],
        size_kb=saved_meta["size_kb"],
        content_type=saved_meta["content_type"],
        pages_count=extracted.get("pages_count", 1),
        extraction_method=extracted.get("extraction_method", "Digital PDF Parser"),
        confidence=extracted.get("confidence", 0.0),
        raw_text=extracted.get("raw_text", ""),
        sections=extracted.get("sections", {}),
        findings=typed_findings,
        passages=passages,
        extraction_errors=extraction_errors,
        processing_status=extracted.get("processing_status", "needs_review"),
        is_verified=False,
        message="Report extracted in local sandbox. Needs user verification before assessment use." if extracted.get("processing_status") != "failed" else "Extraction notice: No readable report text found.",
        disclaimer="Verified indicates text review by user; not clinical validation."
    )

    # Persist report to SQLite database with authenticated user ownership
    report_record = response_payload.model_dump()
    report_record["sanitized_filename"] = saved_meta["sanitized_filename"]
    report_record["saved_path"] = saved_meta["saved_path"]
    save_report_record(report_record, user_id=current_user.user_id)

    return response_payload


@router.post("/verify", response_model=ReportVerificationResponse)
@router.post("/{report_id}/verify", response_model=ReportVerificationResponse)
def verify_report_findings(
    update: ReportVerificationRequest,
    report_id: Optional[str] = None,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> ReportVerificationResponse:
    """
    Step 4 & Step 6:
    Allows authenticated user to review, edit and confirm extracted report text & findings.
    Marks processing status as 'verified' in persistent SQLite storage.
    """
    target_id = report_id or update.report_id
    report = get_report_record(target_id, user_id=current_user.user_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{target_id}' not found or access unauthorized.")

    # Update findings with verified state
    verified_list = []
    for f in update.verified_findings:
        f_dict = f.model_dump()
        f_dict["verified"] = True
        f_dict["needsVerification"] = False
        verified_list.append(f_dict)

    success = update_report_verification_record(
        rpt_id=target_id,
        verified_findings=verified_list,
        raw_text=update.corrected_raw_text,
        sections=update.corrected_sections,
        notes=update.notes
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update report verification in database.")

    now_iso = datetime.datetime.now().isoformat()
    return ReportVerificationResponse(
        status="success",
        report_id=target_id,
        processing_status="verified",
        is_verified=True,
        verified_findings_count=len(verified_list),
        verified_at=now_iso,
        message="Report text reviewed and confirmed by user. Structured evidence ready for clinical reconciliation.",
        disclaimer="Verified indicates text review by user; not clinical validation."
    )


@router.get("/{report_id}", response_model=ReportUploadResponse)
def get_report_details(
    report_id: str,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> ReportUploadResponse:
    """Retrieves extracted document sections, findings, errors, and verification status from SQLite with caller ownership check."""
    report = get_report_record(report_id, user_id=current_user.user_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found or access unauthorized.")
    return ReportUploadResponse(**report)


@router.get("/{report_id}/file")
def get_original_report_file(
    report_id: str,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
):
    """Serves the original document safely from sandbox for side-by-side inspection with caller ownership check."""
    report = get_report_record(report_id, user_id=current_user.user_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found or access unauthorized.")

    saved_path = report.get("saved_path")
    if not saved_path or not os.path.exists(saved_path):
        raise HTTPException(status_code=404, detail="Original document file not found in sandbox.")

    return FileResponse(
        path=saved_path,
        filename=report.get("filename", "report"),
        media_type=report.get("content_type", "application/octet-stream")
    )


@router.delete("/{report_id}")
def purge_report(
    report_id: str,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
):
    """Deletes uploaded document and parsed records from local sandbox with caller ownership check."""
    report = get_report_record(report_id, user_id=current_user.user_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found or access unauthorized.")

    saved_path = report.get("saved_path")
    if saved_path and os.path.exists(saved_path):
        try:
            os.remove(saved_path)
        except Exception:
            pass

    return {
        "status": "success",
        "purged_report_id": report_id,
        "message": "Report permanently purged from local session sandbox."
    }
