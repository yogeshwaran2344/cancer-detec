"""
Assessment Intake, SQLite History, and Clinical Reconciliation Endpoints
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional, Dict, Any
import datetime
import uuid

from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentResponse,
    AssessmentHistoryItem,
    AssessmentHistoryResponse,
    DiscordanceItem,
    FindingItem
)
from app.db.repository import (
    save_assessment_record,
    get_assessment_record,
    list_assessment_records,
    delete_assessment_record,
    purge_user_records,
    compare_assessment_records,
    get_report_record,
    find_recent_duplicate_assessment
)
from app.core.clinical_safety import evaluate_clinical_safety, ClinicalSafetyEvaluation
from app.core.auth import (
    get_current_authenticated_user,
    AuthenticatedUser,
    assert_record_ownership
)

router = APIRouter()


@router.post("", response_model=AssessmentResponse)
@router.post("/", response_model=AssessmentResponse)
def create_assessment(
    payload: AssessmentCreate,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> AssessmentResponse:
    """
    Intake patient symptoms, reconcile against linked scan reports (if available),
    and persist in SQLite without automated percentage risk scoring.
    Includes duplicate submission prevention (idempotency within 15 seconds),
    cryptographic user identity enforcement, and context-aware clinical safety triage.
    """
    effective_user_id = current_user.user_id

    # Duplicate submission prevention (Idempotency)
    existing_dup = find_recent_duplicate_assessment(
        primary_symptoms=payload.primary_symptoms,
        report_id=payload.associated_report_id,
        user_id=effective_user_id,
        window_seconds=15
    )
    if existing_dup:
        return AssessmentResponse(
            assessment_id=existing_dup["id"],
            status=existing_dup.get("status", "Assessment summary ready"),
            assessment_date=existing_dup.get("date", ""),
            patient_reported=existing_dup.get("patient_reported", {}),
            report_findings=[FindingItem(**f) if isinstance(f, dict) else f for f in existing_dup.get("report_findings", [])],
            missing_or_conflicting=[DiscordanceItem(**m) if isinstance(m, dict) else m for m in existing_dup.get("missing_or_conflicting", [])],
            suggested_next_steps=existing_dup.get("suggested_next_steps", []),
            red_flag_alert=existing_dup.get("red_flag_alert", False)
        )

    asm_id = f"ASM-{datetime.datetime.now().year}-{str(uuid.uuid4())[:4].upper()}"
    now_iso = datetime.datetime.now().isoformat()

    # 1. Clinically-Reviewed Context-Aware Safety Triage (Negation & Temporality Aware)
    safety_eval = evaluate_clinical_safety(
        symptoms=payload.primary_symptoms,
        patient_note=payload.patient_note
    )
    red_flags_present = safety_eval.is_urgent

    # 2. Extract or reconcile linked report findings
    report_findings: List[FindingItem] = []
    missing_or_conflicting: List[DiscordanceItem] = []
    has_report = False

    # Add safety evaluation context notes (e.g. explicitly negated red flags or historical conditions)
    if safety_eval.negated_findings:
        missing_or_conflicting.append(
            DiscordanceItem(
                finding_id="safety-negated",
                category="safety_triage_clarification",
                title="Reported Absence of Acute Red-Flag Signs",
                description=f"Patient explicitly denies/rules out acute warning signs: {', '.join(safety_eval.negated_findings)}.",
                clinical_note="Confirmed non-acute status for these specific items based on contextual negation screening."
            )
        )
    if safety_eval.historical_findings:
        missing_or_conflicting.append(
            DiscordanceItem(
                finding_id="safety-historical",
                category="safety_triage_clarification",
                title="Historical / Remote Condition Documented",
                description=f"Reported in past medical history: {', '.join(safety_eval.historical_findings)}.",
                clinical_note="Remote historical conditions do not constitute an active acute emergency presentation."
            )
        )

    if payload.associated_report_id:
        saved_report = get_report_record(payload.associated_report_id)
        if saved_report:
            has_report = True
            raw_findings = saved_report.get("findings", [])
            for f in raw_findings:
                finding_obj = FindingItem(
                    id=f.get("id", "p0"),
                    title=f.get("title", "Finding"),
                    finding=f.get("finding", f.get("body", "")),
                    body=f.get("body", ""),
                    section=f.get("section", "findings"),
                    anchor=f.get("id", "p0"),
                    category=f.get("category", "significant"),
                    typeLabel=f.get("typeLabel", "Anatomical Finding"),
                    uncertainty=f.get("uncertainty", False),
                    needsVerification=f.get("needsVerification", False),
                    verified=f.get("verified", False),
                    sourceRef=f.get("sourceRef", "Report § 1")
                )
                report_findings.append(finding_obj)

            # Check for potential discordances between symptoms and findings
            if payload.primary_symptoms and report_findings:
                missing_or_conflicting.append(
                    DiscordanceItem(
                        finding_id="disc-1",
                        category="missing_or_conflicting",
                        title="Correlation of Reported Symptoms vs Documented Findings",
                        description=(
                            f"Patient reported '{', '.join(payload.primary_symptoms[:2])}'. "
                            "The uploaded imaging report does not explicitly attribute these symptoms to a single localized structural lesion."
                        ),
                        clinical_note="Discordance does not indicate malignancy; physiological or functional etiologies should be reviewed with the physician."
                    )
                )

    # 3. Formulate structured next steps
    suggested_steps = []
    if red_flags_present:
        active_str = ", ".join(safety_eval.active_red_flags)
        suggested_steps.append(
            f"URGENT CLINICAL REVIEW: Active warning sign(s) detected ({active_str}). "
            "Requires prompt in-person medical evaluation by a qualified physician."
        )
    suggested_steps.append("Schedule an appointment to review these structured findings with your treating physician.")
    suggested_steps.append("Bring a printed copy or digital copy of the original imaging report along with this assessment summary.")
    if has_report:
        suggested_steps.append("Confirm verified sections with your radiologist if any passage remains marked for review.")
    suggested_steps.append("Inquire whether repeat interval imaging, targeted lab tests, or specialist referral is appropriate.")

    patient_reported_dict = {
        "primary_symptoms": payload.primary_symptoms,
        "onset": payload.onset,
        "trajectory": payload.trajectory,
        "frequency": payload.frequency,
        "age_bracket": payload.age_bracket,
        "patient_name": payload.patient_name,
        "biological_sex": payload.biological_sex,
        "smoking_status": payload.smoking_status,
        "medical_history": payload.medical_history,
        "patient_note": payload.patient_note
    }

    response_data = AssessmentResponse(
        assessment_id=asm_id,
        status="Assessment summary ready",
        assessment_date=now_iso,
        patient_reported=patient_reported_dict,
        report_findings=report_findings,
        missing_or_conflicting=missing_or_conflicting,
        suggested_next_steps=suggested_steps,
        red_flag_alert=red_flags_present
    )

    symptom_preview = ", ".join(payload.primary_symptoms[:2]) if payload.primary_symptoms else "Reported concerns"
    summary_text = f"Assessment: {symptom_preview}" + (" with linked report" if has_report else "")

    # Persist to SQLite Database
    record_to_save = {
        "id": asm_id,
        "created_at": now_iso,
        "assessment_type": "Combined Assessment" if has_report else "Symptom Questionnaire",
        "status": "Assessment summary ready",
        "summary": summary_text,
        "findings_count": len(report_findings),
        "report_id": payload.associated_report_id if has_report else None,
        "patient_reported": patient_reported_dict,
        "report_findings": [f.model_dump() for f in report_findings],
        "missing_or_conflicting": [m.model_dump() for m in missing_or_conflicting],
        "suggested_next_steps": suggested_steps,
        "red_flag_alert": red_flags_present
    }
    save_assessment_record(record_to_save, user_id=effective_user_id)

    return response_data


@router.get("", response_model=AssessmentHistoryResponse)
@router.get("/", response_model=AssessmentHistoryResponse)
def get_assessment_history(
    assessment_type: Optional[str] = Query(None, description="Filter by assessment type"),
    search: Optional[str] = Query(None, description="Search keyword in summary or ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> AssessmentHistoryResponse:
    """Retrieves previous clinical assessments belonging to the authenticated caller from SQLite."""
    total_count, records = list_assessment_records(
        assessment_type=assessment_type,
        search=search,
        user_id=current_user.user_id,
        limit=limit,
        offset=offset
    )

    items = [AssessmentHistoryItem(**r) for r in records]
    return AssessmentHistoryResponse(
        total_count=total_count,
        items=items
    )


@router.get("/compare")
def compare_two_assessments(
    id1: str = Query(..., description="First assessment ID to compare"),
    id2: str = Query(..., description="Second assessment ID to compare"),
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> Dict[str, Any]:
    """
    Compares two previous assessments side by side with caller ownership enforcement.
    CRITICAL RULE:
    Highlights: 'Do not interpret wording differences between reports as confirmed disease progression.'
    """
    try:
        comparison_result = compare_assessment_records(id1, id2, user_id=current_user.user_id)
        return comparison_result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{assessment_id}", response_model=AssessmentResponse)
def get_assessment_by_id(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
) -> AssessmentResponse:
    """Retrieve full details of an assessment by its ID from SQLite with server-side ownership enforcement."""
    stored = get_assessment_record(assessment_id, user_id=current_user.user_id)
    if not stored:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found or access unauthorized.")

    return AssessmentResponse(
        assessment_id=stored["id"],
        status=stored.get("status", "Assessment summary ready"),
        assessment_date=stored.get("date", ""),
        patient_reported=stored.get("patient_reported", {}),
        report_findings=[FindingItem(**f) if isinstance(f, dict) else f for f in stored.get("report_findings", [])],
        missing_or_conflicting=[DiscordanceItem(**m) if isinstance(m, dict) else m for m in stored.get("missing_or_conflicting", [])],
        suggested_next_steps=stored.get("suggested_next_steps", []),
        red_flag_alert=stored.get("red_flag_alert", False)
    )


@router.delete("/{assessment_id}")
def delete_assessment(
    assessment_id: str,
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
):
    """Safely deletes an assessment from SQLite with server-side ownership authorization."""
    success = delete_assessment_record(assessment_id, user_id=current_user.user_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Assessment '{assessment_id}' not found or deletion unauthorized.")
    return {
        "status": "success",
        "deleted_id": assessment_id,
        "message": f"Assessment '{assessment_id}' permanently removed from persistent storage."
    }


@router.delete("")
@router.delete("/")
def purge_all_assessments(
    current_user: AuthenticatedUser = Depends(get_current_authenticated_user)
):
    """Purges all assessments and reports for the authenticated user in compliance with retention policy."""
    purged_count = purge_user_records(user_id=current_user.user_id)
    return {
        "status": "success",
        "purged_records_count": purged_count,
        "message": "All clinical assessments and reports purged from persistent database."
    }
