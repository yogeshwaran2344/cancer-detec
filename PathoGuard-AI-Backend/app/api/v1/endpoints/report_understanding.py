"""
AI Report Understanding & Grounded Evidence Search API Endpoints
Provides section-by-section patient translations, medical terminology explanations,
grounded evidence search, and abstention safeguards against unsupported conclusions.
"""

from fastapi import APIRouter, HTTPException, Query, Path
from typing import Optional, Dict, Any

from app.db.repository import get_report_record
from app.engine.report_explainer import ReportUnderstandingEngine
from app.engine.terminology_explainer import explain_medical_term, CLINICAL_GLOSSARY
from app.engine.abstention_rules import AbstentionEvaluator
from app.schemas.report_understanding import (
    ReportExplanationResponse,
    EvidenceSearchRequest,
    EvidenceSearchResponse,
    ClaimEvaluationRequest,
    ClaimEvaluationResponse,
    TermExplanation
)

router = APIRouter()


@router.get("/{report_id}/explain", response_model=ReportExplanationResponse)
@router.post("/{report_id}/explain", response_model=ReportExplanationResponse)
def get_report_ai_explanation(
    report_id: str = Path(..., description="Report ID stored in database"),
    user_id: Optional[str] = Query(None, description="User ownership verification")
) -> ReportExplanationResponse:
    """
    Step 1 & Step 2:
    Generates grounded patient-friendly explanations for all findings and sections
    of a verified report, strictly linking explanations to original verbatim text passages.
    """
    report = get_report_record(report_id, user_id=user_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found in database.")

    explanation = ReportUnderstandingEngine.generate_full_explanation(report)
    return ReportExplanationResponse(**explanation)


@router.post("/{report_id}/search-evidence", response_model=EvidenceSearchResponse)
def search_evidence_in_report(
    payload: EvidenceSearchRequest,
    report_id: str = Path(..., description="Report ID to search"),
    user_id: Optional[str] = Query(None, description="User ownership verification")
) -> EvidenceSearchResponse:
    """
    Step 2 & Step 5:
    Searches report text for grounded passage anchors matching a user query.
    Enforces abstention if the query requests unsupported diagnostic conclusions.
    """
    report = get_report_record(report_id, user_id=user_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report '{report_id}' not found in database.")

    search_result = ReportUnderstandingEngine.search_evidence(report, payload.query)
    return EvidenceSearchResponse(**search_result)


@router.post("/check-claim", response_model=ClaimEvaluationResponse)
def evaluate_interpretation_claim(payload: ClaimEvaluationRequest) -> ClaimEvaluationResponse:
    """
    Step 5:
    Evaluates whether an interpretation claim or question is medically grounded or
    requires abstention (e.g. attempting to diagnose malignancy from imaging alone).
    """
    report_text = payload.report_text or ""
    if payload.report_id and not report_text:
        report = get_report_record(payload.report_id)
        if report:
            report_text = report.get("raw_text", "")

    evaluation = AbstentionEvaluator.evaluate_interpretation(payload.claim_or_question, report_text)
    return ClaimEvaluationResponse(
        claim_or_question=payload.claim_or_question,
        should_abstain=evaluation["should_abstain"],
        abstention_category=evaluation["abstention_category"],
        reason=evaluation["reason"],
        clinical_safeguard=evaluation["clinical_safeguard"],
        recommended_action=evaluation["recommended_action"]
    )


@router.get("/terms/{term}", response_model=TermExplanation)
def get_term_explanation(term: str = Path(..., description="Medical or radiological term to define")) -> TermExplanation:
    """
    Step 3:
    Returns a grounded, plain-language patient translation of a clinical term,
    with common misconceptions and suggested doctor questions.
    """
    data = explain_medical_term(term)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Clinical term '{term}' not found in current grounded vocabulary."
        )
    return TermExplanation(**data)
