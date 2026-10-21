"""
PathoGuard-AI — Minimum-Information Acquisition Engine (Feature 3)
Active clinical uncertainty reduction engine that formulates evidence gaps and determines
the highest-utility, lowest-burden next step for the patient and clinician.
Prevents questionnaire fatigue and recognizes when technical questions exceed patient competence.
"""

from typing import Dict, List, Any, Optional
import math


class GapType:
    SYMPTOM_TEMPORAL_DURATION = "SYMPTOM_TEMPORAL_DURATION"
    RED_FLAG_SEVERITY_CHECK = "RED_FLAG_SEVERITY_CHECK"
    MISSING_PRIOR_SCAN = "MISSING_PRIOR_SCAN"
    OCR_CORRUPTED_TEXT = "OCR_CORRUPTED_TEXT"
    HISTOLOGY_RECEPTOR_STATUS = "HISTOLOGY_RECEPTOR_STATUS"
    SMOKING_FAMILY_HISTORY = "SMOKING_FAMILY_HISTORY"


class InformationGap:
    def __init__(
        self,
        gap_id: str,
        gap_type: str,
        description: str,
        uncertainty_reduction: float,  # 0.0 to 1.0
        patient_burden: float,         # 0.0 (trivial) to 1.0 (exhausting)
        patient_solvable: bool,        # Can a patient answer this or does it need clinical records?
        suggested_action: str,
        question_prompt: Optional[str] = None
    ):
        self.gap_id = gap_id
        self.gap_type = gap_type
        self.description = description
        self.uncertainty_reduction = max(0.0, min(1.0, uncertainty_reduction))
        self.patient_burden = max(0.0, min(1.0, patient_burden))
        self.patient_solvable = patient_solvable
        self.suggested_action = suggested_action
        self.question_prompt = question_prompt

    @property
    def utility_score(self) -> float:
        """
        Information Acquisition Utility Score:
        Balances high information gain against patient cognitive burden.
        Penalizes questions that lay patients cannot reliably self-report.
        """
        solvability_weight = 1.0 if self.patient_solvable else 0.15
        burden_penalty = 1.0 + (0.6 * self.patient_burden)
        raw_score = (self.uncertainty_reduction / burden_penalty) * solvability_weight
        return round(raw_score, 4)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type,
            "description": self.description,
            "uncertainty_reduction": self.uncertainty_reduction,
            "patient_burden": self.patient_burden,
            "patient_solvable": self.patient_solvable,
            "utility_score": self.utility_score,
            "suggested_action": self.suggested_action,
            "question_prompt": self.question_prompt
        }


class MinimumInformationAcquisitionEngine:
    """
    Selects the single most valuable next action rather than subjecting the patient
    to an exhaustive 25-question intake battery.
    """

    @classmethod
    def identify_gaps(
        cls,
        report_data: Optional[Dict[str, Any]] = None,
        symptom_data: Optional[Dict[str, Any]] = None,
        prior_reports: Optional[List[Dict[str, Any]]] = None
    ) -> List[InformationGap]:
        gaps: List[InformationGap] = []
        rpt = report_data or {}
        sym = symptom_data or {}
        priors = prior_reports or []

        findings = rpt.get("findings", [])
        sections = rpt.get("sections", {})
        extraction_errors = rpt.get("extraction_errors", [])

        # Gap 1: OCR Extraction Corrupted
        if extraction_errors or len(sections.get("findings", "")) < 15:
            gaps.append(InformationGap(
                gap_id="GAP-OCR-RESYNCHRONIZE",
                gap_type=GapType.OCR_CORRUPTED_TEXT,
                description="Report text extraction has unreadable or truncated sections.",
                uncertainty_reduction=0.92,
                patient_burden=0.20,  # Easy: just upload a cleaner picture or review scan
                patient_solvable=True,
                suggested_action="PROMPT_USER_IMAGE_RESCAN",
                question_prompt="Would you like to re-upload a clearer image or manually confirm the findings section?"
            ))

        # Gap 2: Red Flag Symptoms Unconfirmed
        symptoms_list = sym.get("symptoms", [])
        has_weight_loss = any("weight" in str(s).lower() for s in symptoms_list)
        has_hemoptysis = any("blood" in str(s).lower() or "hemoptysis" in str(s).lower() for s in symptoms_list)

        if not has_weight_loss and not has_hemoptysis:
            gaps.append(InformationGap(
                gap_id="GAP-RED-FLAG-SCREENING",
                gap_type=GapType.RED_FLAG_SEVERITY_CHECK,
                description="Critical systemic red flags (unexplained weight loss or hemoptysis) have not been screened.",
                uncertainty_reduction=0.88,
                patient_burden=0.10,  # Quick yes/no
                patient_solvable=True,
                suggested_action="INQUIRE_TARGETED_RED_FLAGS",
                question_prompt="Have you noticed any unintended weight loss (>5 kg) or coughing up blood in the past month?"
            ))

        # Gap 3: Symptom Duration & Onset
        duration = sym.get("duration") or sym.get("symptom_duration")
        if not duration or duration == "unknown":
            gaps.append(InformationGap(
                gap_id="GAP-TEMPORAL-ONSET",
                gap_type=GapType.SYMPTOM_TEMPORAL_DURATION,
                description="Duration and chronicity of reported symptoms are unknown.",
                uncertainty_reduction=0.75,
                patient_burden=0.15,
                patient_solvable=True,
                suggested_action="INQUIRE_SYMPTOM_ONSET",
                question_prompt="Approximately how long have you been experiencing these symptoms (days, weeks, or months)?"
            ))

        # Gap 4: Missing Prior Imaging for Longitudinal Context
        if not priors and len(findings) > 0:
            gaps.append(InformationGap(
                gap_id="GAP-PRIOR-STUDY-RETRIEVAL",
                gap_type=GapType.MISSING_PRIOR_SCAN,
                description="Single point-in-time study without prior baseline to determine stability vs progression.",
                uncertainty_reduction=0.85,
                patient_burden=0.35,  # Requires finding and uploading another document
                patient_solvable=True,
                suggested_action="REQUEST_HISTORICAL_BASELINE_REPORT",
                question_prompt="Do you have any previous scan reports of this same region from 6–12 months ago to compare?"
            ))

        # Gap 5: High Technicality Histology Gap (NOT patient solvable)
        has_mass = any("mass" in str(f).lower() or "nodule" in str(f).lower() for f in findings)
        if has_mass and not any("receptor" in str(f).lower() or "ki-67" in str(f).lower() for f in findings):
            gaps.append(InformationGap(
                gap_id="GAP-HISTOPATHOLOGY-IMMUNOHISTOCHEMISTRY",
                gap_type=GapType.HISTOLOGY_RECEPTOR_STATUS,
                description="Immunohistochemical marker profile and molecular pathology status are absent.",
                uncertainty_reduction=0.95,
                patient_burden=0.90,  # Lay patient cannot answer molecular biology
                patient_solvable=False,  # MUST NOT ask patient
                suggested_action="ESCALATE_TO_PHYSICIAN_BIOPSY_REVIEW",
                question_prompt=None  # Do not ask patient directly
            ))

        return gaps

    @classmethod
    def determine_optimal_next_action(
        cls,
        report_data: Optional[Dict[str, Any]] = None,
        symptom_data: Optional[Dict[str, Any]] = None,
        prior_reports: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Calculates utility across all identified information gaps and recommends the optimal next step.
        Enforces a patient burden budget to prevent excessive interrogation.
        """
        all_gaps = cls.identify_gaps(report_data, symptom_data, prior_reports)

        # Sort gaps by descending utility score
        sorted_gaps = sorted(all_gaps, key=lambda g: g.utility_score, reverse=True)

        if not sorted_gaps:
            return {
                "next_action": "PROCEED_TO_ASSESSMENT_SYNTHESIS",
                "recommended_gap": None,
                "utility_score": 1.0,
                "reason": "All critical information requirements are satisfied."
            }

        top_gap = sorted_gaps[0]

        # Clinical Safety Check: If top gap is NOT patient solvable, abstain from interrogation
        if not top_gap.patient_solvable:
            return {
                "next_action": "ESCALATE_TO_SPECIALIST_REVIEW",
                "recommended_gap": top_gap.to_dict(),
                "all_gaps_evaluated": [g.to_dict() for g in sorted_gaps],
                "patient_interrogation_status": "HALTED_TECHNICAL_LIMIT",
                "rationale": (
                    f"Top clinical uncertainty ({top_gap.gap_id}) requires professional pathology / specialist record review. "
                    "Abstaining from patient interrogation to prevent misinformation."
                )
            }

        return {
            "next_action": top_gap.suggested_action,
            "recommended_gap": top_gap.to_dict(),
            "all_gaps_evaluated": [g.to_dict() for g in sorted_gaps],
            "patient_interrogation_status": "ACTIVE_TARGETED_INQUIRY",
            "question_for_patient": top_gap.question_prompt,
            "utility_score": top_gap.utility_score,
            "rationale": (
                f"Selected '{top_gap.gap_id}' with optimal uncertainty reduction ({top_gap.uncertainty_reduction}) "
                f"at manageable patient burden ({top_gap.patient_burden})."
            )
        }
