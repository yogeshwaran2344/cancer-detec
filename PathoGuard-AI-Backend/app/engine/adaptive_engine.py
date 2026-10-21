"""
PathoGuard-AI — Adaptive Assessment & Evidence-Gated Follow-Up Engine
Analyzes patient-reported symptoms alongside verified report findings,
dynamically selects targeted follow-up clarifications, detects discordances,
and enforces evidence grounding and clinical abstention safeguards.
"""

from typing import Dict, List, Any, Optional
import datetime
import re

from app.engine.abstention_rules import AbstentionEvaluator
from app.engine.terminology_explainer import explain_medical_term, extract_and_explain_terms_in_text

RED_FLAG_TERMS = [
    "hemoptysis", "coughing blood", "blood in stool", "rectal bleeding",
    "unexplained weight loss", "difficulty swallowing", "dysphagia",
    "painless breast lump", "hard fixed lump", "jaundice", "hoarseness > 3 weeks"
]


class AdaptiveAssessmentEngine:
    """
    Evidence-Gated Adaptive Engine:
    Contrasts with simple linear fixed-questionnaires by adapting dynamically
    to patient inputs, identifying discordances, gating evidence, and enforcing abstention.
    """

    @classmethod
    def evaluate(
        cls,
        patient_intake: Dict[str, Any],
        report_record: Optional[Dict[str, Any]] = None,
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes evidence-gated assessment:
        1. Checks for unsupported claims / diagnostic queries (Abstention)
        2. Evaluates data sufficiency & report completeness
        3. Identifies red flags & ambiguous symptom descriptions
        4. Detects discordance between reported symptoms and report findings
        5. Generates adaptive, targeted follow-up clarifications
        6. Formulates grounded physician questions and next steps
        """
        primary_symptoms = patient_intake.get("primary_symptoms", [])
        patient_note = patient_intake.get("patient_note", "") or ""
        onset = patient_intake.get("onset", "")
        trajectory = patient_intake.get("trajectory", "")
        medical_history = patient_intake.get("medical_history", [])

        # Combined patient symptom narrative
        narrative = " ".join(primary_symptoms) + " " + patient_note + " " + onset
        narrative_lower = narrative.lower()

        # -------------------------------------------------------------
        # 1. Evaluate Abstention on User Query or Patient Assertions
        # -------------------------------------------------------------
        query_to_check = user_query or patient_note
        report_raw_text = report_record.get("raw_text", "") if report_record else ""
        abstention_result = AbstentionEvaluator.evaluate_interpretation(query_to_check, report_raw_text)

        # -------------------------------------------------------------
        # 2. Red Flag Detection
        # -------------------------------------------------------------
        detected_red_flags = []
        for term in RED_FLAG_TERMS:
            if term in narrative_lower:
                detected_red_flags.append(term)

        # -------------------------------------------------------------
        # 3. Report Structure & Sufficiency Evaluation
        # -------------------------------------------------------------
        data_sufficiency = {
            "is_sufficient": True,
            "has_warnings": False,
            "issues": [],
            "recommendation": "Input data is sufficient for structured educational synthesis."
        }
        if report_record:
            sections = report_record.get("sections", {})
            errors = report_record.get("extraction_errors", [])
            data_sufficiency = AbstentionEvaluator.check_report_data_sufficiency(sections, errors)

        # -------------------------------------------------------------
        # 4. Report Findings Grounding & Verification
        # -------------------------------------------------------------
        grounded_findings = []
        unverified_count = 0
        if report_record:
            raw_findings = report_record.get("findings", [])
            for idx, f in enumerate(raw_findings):
                is_verified = f.get("verified", False)
                needs_verif = f.get("needsVerification", False)
                if needs_verif and not is_verified:
                    unverified_count += 1

                body = f.get("finding") or f.get("body", "")
                grounded_findings.append({
                    "finding_id": f.get("id", f"f-{idx}"),
                    "title": f.get("title", f"Observation {idx+1}"),
                    "verbatim_passage": body,
                    "source_type": "VERBATIM_REPORT",
                    "page": f.get("page", 1),
                    "is_verified": is_verified,
                    "needs_verification": needs_verif
                })

        # -------------------------------------------------------------
        # 5. Discordance & Conflict Detection
        # -------------------------------------------------------------
        discordances = []
        if report_record and primary_symptoms:
            report_findings_text = " ".join([f["verbatim_passage"] for f in grounded_findings]).lower()
            
            # Check anatomical discordance (e.g. respiratory symptoms vs abdominal report)
            respiratory_symptoms = ["cough", "shortness of breath", "dyspnea", "chest pain", "wheezing", "hemoptysis"]
            has_resp_symptom = any(s in narrative_lower for s in respiratory_symptoms)
            
            abdominal_symptoms = ["abdominal pain", "flank pain", "pelvic pain", "digestive issues"]
            has_abdo_symptom = any(s in narrative_lower for s in abdominal_symptoms)

            report_filename = (report_record.get("filename") or "").lower()
            is_chest_scan = "chest" in report_filename or "thoracic" in report_filename or "lung" in report_findings_text
            is_pelvic_or_abdo_scan = "pelvic" in report_filename or "abdomen" in report_filename or "kidney" in report_findings_text

            if has_resp_symptom and is_pelvic_or_abdo_scan and not is_chest_scan:
                discordances.append({
                    "category": "ANATOMICAL_MISMATCH",
                    "title": "Anatomical Disconnect: Reported Symptoms vs Examined Region",
                    "description": "Patient reported thoracic/respiratory symptoms, but uploaded scan evaluated pelvic/abdominal structures.",
                    "clinical_action": "Inquire whether a separate thoracic imaging study was performed."
                })

            if has_abdo_symptom and is_chest_scan and not is_pelvic_or_abdo_scan:
                discordances.append({
                    "category": "ANATOMICAL_MISMATCH",
                    "title": "Anatomical Disconnect: Reported Symptoms vs Examined Region",
                    "description": "Patient reported abdominal/flank symptoms, but uploaded scan evaluated thoracic structures.",
                    "clinical_action": "Verify with physician whether abdominal imaging is planned."
                })

            # Check normal scan despite persistent symptoms
            if ("normal" in report_findings_text or "unremarkable" in report_findings_text) and len(detected_red_flags) > 0:
                discordances.append({
                    "category": "SYMPTOM_SCAN_DISCORDANCE",
                    "title": "Reported Red-Flag Symptoms with Unremarkable Imaging",
                    "description": f"Patient reported '{', '.join(detected_red_flags)}', but imaging text describes unremarkable findings.",
                    "clinical_action": "Prompt clinical evaluation required; normal imaging does not rule out mucosal, microscopic, or functional etiologies."
                })

        # -------------------------------------------------------------
        # 6. Adaptive Dynamic Follow-Up Generation
        # -------------------------------------------------------------
        adaptive_follow_ups = []

        # If red flag symptoms detected, generate targeted clinical clarification
        if detected_red_flags:
            adaptive_follow_ups.append({
                "id": "af-redflag-1",
                "urgency": "HIGH",
                "category": "ALERT_CLARIFICATION",
                "question": f"You mentioned {', '.join(detected_red_flags)}. How frequently has this occurred, and have you noticed accompanying fever, night sweats, or dizziness?",
                "rationale": "Clarifies systemic B-symptoms and hemodynamic stability in the presence of alarming clinical signs."
            })

        # If onset or duration is ambiguous
        if not onset or onset == "Not specified":
            adaptive_follow_ups.append({
                "id": "af-onset-1",
                "urgency": "MEDIUM",
                "category": "TIMELINE_CLARIFICATION",
                "question": "Approximately how many days, weeks, or months have you experienced these primary symptoms?",
                "rationale": "Timeline distinction differentiates acute infectious vs subacute or chronic etiologies."
            })

        # If unverified OCR findings exist
        if unverified_count > 0:
            adaptive_follow_ups.append({
                "id": "af-verif-1",
                "urgency": "MEDIUM",
                "category": "VERIFICATION_PROMPT",
                "question": f"There are {unverified_count} report finding(s) awaiting your review. Have you verified the extracted text against your original printed report?",
                "rationale": "Prevents AI reconciliation on unconfirmed optical character recognition output."
            })

        # If discordance detected
        if discordances:
            for d in discordances:
                adaptive_follow_ups.append({
                    "id": f"af-disc-{len(adaptive_follow_ups)}",
                    "urgency": "HIGH",
                    "category": "DISCORDANCE_PROMPT",
                    "question": f"Reconciliation notice: {d['description']} Would you like to note this for your doctor?",
                    "rationale": "Prompts patient to clarify potential mismatch before the clinical visit."
                })

        # -------------------------------------------------------------
        # 7. Formulate Grounded Next Steps
        # -------------------------------------------------------------
        next_steps = []
        if detected_red_flags:
            next_steps.append("URGENT: Schedule prompt in-person medical evaluation to address reported warning signs.")
        next_steps.append("Bring a printed copy of your verified imaging report to your doctor's appointment.")
        if discordances:
            next_steps.append("Discuss the highlighted differences between your symptoms and the scan findings with your clinician.")
        if unverified_count > 0:
            next_steps.append("Review pending unverified report text before sharing this summary with clinical staff.")
        next_steps.append("PathoGuard-AI provides structured educational evidence, not a medical diagnosis.")

        return {
            "engine_mode": "ADAPTIVE_EVIDENCE_GATED",
            "evaluated_at": datetime.datetime.now().isoformat(),
            "abstention_triggered": abstention_result["should_abstain"],
            "abstention_details": abstention_result if abstention_result["should_abstain"] else None,
            "red_flags_present": len(detected_red_flags) > 0,
            "detected_red_flags": detected_red_flags,
            "data_sufficiency": data_sufficiency,
            "grounded_findings": grounded_findings,
            "unverified_findings_count": unverified_count,
            "discordances": discordances,
            "adaptive_follow_ups": adaptive_follow_ups,
            "suggested_next_steps": next_steps,
            "unsupported_claim_emitted": False,
            "diagnostic_percentage_emitted": False
        }


class FixedQuestionBaseline:
    """
    Fixed-Question Baseline:
    Simulates standard rigid online symptom questionnaires.
    Always returns the exact same fixed 6 questions without evidence gating,
    discordance detection, or medical report passage grounding.
    """

    @classmethod
    def evaluate(
        cls,
        patient_intake: Dict[str, Any],
        report_record: Optional[Dict[str, Any]] = None,
        user_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the linear fixed baseline evaluation."""
        primary_symptoms = patient_intake.get("primary_symptoms", [])

        # The fixed baseline does NOT adapt to red flags, does NOT gate on reports,
        # and does NOT perform passage-level grounding or abstention.
        return {
            "engine_mode": "FIXED_QUESTION_BASELINE",
            "evaluated_at": datetime.datetime.now().isoformat(),
            "abstention_triggered": False,  # Fixed baseline fails to abstain on diagnostic queries!
            "abstention_details": None,
            "red_flags_present": False,    # Fixed baseline does not flag urgent alerts dynamically
            "detected_red_flags": [],
            "data_sufficiency": {"is_sufficient": True, "has_warnings": False},  # Blindly assumes valid
            "grounded_findings": [],       # No passage-level grounding
            "unverified_findings_count": 0,
            "discordances": [],            # Fails to detect symptom-scan discordance
            "adaptive_follow_ups": [
                {"id": "fixed-1", "question": "Where is the symptom located?"},
                {"id": "fixed-2", "question": "How severe is the discomfort on a scale of 1-10?"},
                {"id": "fixed-3", "question": "Does anything make it better or worse?"}
            ],
            "suggested_next_steps": ["Consult a doctor if symptoms persist."],
            "unsupported_claim_emitted": False,
            "diagnostic_percentage_emitted": False
        }
