"""
Schemas for AI Report Understanding & Grounded Evidence Search
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any


class TermExplanation(BaseModel):
    term: str
    simple_definition: str
    clinical_context: str
    common_misconception: Optional[str] = None
    doctor_question: Optional[str] = None


class GroundedFindingExplanation(BaseModel):
    finding_id: str
    title: str
    verbatim_passage: str
    source_type: str = "VERBATIM_REPORT"
    source_ref: str
    page: int = 1
    is_verified_by_user: bool = False
    uncertainty_flag: bool = False
    ai_plain_language_summary: str
    ai_explanation_source: str = "AI_PATIENT_EXPLANATION"
    medical_terms: List[Dict[str, Any]] = []
    suggested_doctor_question: Optional[str] = None


class ExplainedSection(BaseModel):
    section_key: str
    section_title: str
    verbatim_text: str
    source_type: str = "VERBATIM_REPORT"
    page_reference: str = "Page 1"
    ai_plain_language_explanation: str
    ai_explanation_source: str = "AI_PATIENT_EXPLANATION"
    medical_terms_explained: List[Dict[str, Any]] = []
    doctor_questions: List[str] = []


class ReportExplanationResponse(BaseModel):
    status: str = "success"
    report_id: str
    filename: str
    verification_status: str
    is_verified: bool
    data_sufficiency: Dict[str, Any]
    explained_sections: List[ExplainedSection]
    grounded_findings: List[GroundedFindingExplanation]
    overall_clinical_notice: str
    generated_at: str


class EvidenceSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, description="Search keyword, symptom, or question")


class EvidenceSearchResponse(BaseModel):
    status: str
    query: str
    report_id: str
    abstention_triggered: bool
    abstention_details: Optional[Dict[str, Any]] = None
    matches_count: int = 0
    matching_passages: List[Dict[str, Any]] = []
    disclaimer: str


class ClaimEvaluationRequest(BaseModel):
    claim_or_question: str
    report_id: Optional[str] = None
    report_text: Optional[str] = None


class ClaimEvaluationResponse(BaseModel):
    claim_or_question: str
    should_abstain: bool
    abstention_category: str
    reason: str
    clinical_safeguard: str
    recommended_action: str
