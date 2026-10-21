"""
Assessment Schemas (Intake, Reconciliation, and History)
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class AssessmentCreate(BaseModel):
    primary_symptoms: List[str] = Field(default_factory=list, description="Reported patient symptoms")
    onset: Optional[str] = Field(None, description="Onset timing e.g. '3-6 weeks'")
    trajectory: Optional[str] = Field(None, description="Symptom trajectory e.g. 'Worsening'")
    frequency: Optional[str] = Field(None, description="Frequency e.g. 'Constant'")
    age_bracket: Optional[str] = Field(None, description="Patient age category")
    patient_name: Optional[str] = Field(None, description="Patient full name")
    biological_sex: Optional[str] = Field(None, description="Biological sex / gender identity")
    smoking_status: Optional[str] = Field(None, description="Smoking & environmental exposure history")
    medical_history: Optional[List[str]] = Field(default_factory=list, description="Pre-existing conditions")
    patient_note: Optional[str] = Field(None, description="Free text user comments")
    associated_report_id: Optional[str] = Field(None, description="Linked uploaded report ID")


class FindingItem(BaseModel):
    id: str = "p0"
    title: Optional[str] = None
    finding: Optional[str] = None
    body: Optional[str] = None
    section: str = "findings"
    anchor: Optional[str] = "p0"
    category: Optional[str] = "significant"
    typeLabel: Optional[str] = None
    uncertainty: bool = False
    needsVerification: bool = False
    verified: bool = False
    sourceRef: Optional[str] = None
    evidence_text: Optional[str] = None


class DiscordanceItem(BaseModel):
    finding_id: str
    category: str = "missing_or_conflicting"
    title: str = "Discordance Note"
    description: str
    clinical_note: str


class ReconciliationRequest(BaseModel):
    symptom_data: AssessmentCreate
    report_findings: List[FindingItem] = Field(default_factory=list)


class AssessmentResponse(BaseModel):
    assessment_id: str
    status: str = "Assessment summary ready"
    assessment_date: str
    patient_reported: Dict[str, Any]
    report_findings: List[FindingItem] = []
    missing_or_conflicting: List[DiscordanceItem] = []
    suggested_next_steps: List[str] = []
    red_flag_alert: bool = False
    disclaimer: str = (
        "PathoGuard-AI provides clinical reconciliation and decision-support assistance only. "
        "It does not provide medical diagnoses, rule out malignancy, or generate automated cancer percentage risk."
    )


class AssessmentHistoryItem(BaseModel):
    id: str
    date: str
    type: str
    status: str
    summary: str
    findings_count: int = 0
    report_linked: bool = False


class AssessmentHistoryResponse(BaseModel):
    total_count: int
    items: List[AssessmentHistoryItem]
