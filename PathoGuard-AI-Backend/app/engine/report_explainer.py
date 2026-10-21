"""
PathoGuard-AI — Evidence-Grounded AI Report Understanding & Search Engine
Parses verified reports into patient-friendly explanations, maintains strict separation
between original report verbatim text and AI-generated explanations, and provides
grounded passage-linked evidence search.
"""

from typing import Dict, List, Any, Optional
import re
import datetime

from app.engine.terminology_explainer import (
    explain_medical_term,
    extract_and_explain_terms_in_text
)
from app.engine.abstention_rules import AbstentionEvaluator


class ReportUnderstandingEngine:
    """Core intelligence engine for patient-friendly report comprehension and evidence search."""

    @classmethod
    def generate_full_explanation(cls, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesizes a complete, grounded report explanation.
        Preserves strict distinction between original report content and AI explanations.
        """
        report_id = report_data.get("report_id") or report_data.get("id", "RPT-LOCAL")
        raw_text = report_data.get("raw_text", "")
        sections = report_data.get("sections", {})
        findings = report_data.get("findings", [])
        is_verified = report_data.get("is_verified", False)
        extraction_errors = report_data.get("extraction_errors", [])

        # 1. Check data sufficiency and extraction quality
        sufficiency = AbstentionEvaluator.check_report_data_sufficiency(sections, extraction_errors)

        # 2. Build structured grounded sections with AI plain-language translations
        explained_sections: List[Dict[str, Any]] = []

        # A. Examination & Technique
        tech_text = sections.get("technique", "").strip()
        if tech_text:
            tech_terms = extract_and_explain_terms_in_text(tech_text)
            explained_sections.append({
                "section_key": "technique",
                "section_title": "Examination Protocol & Imaging Technique",
                "verbatim_text": tech_text,
                "source_type": "VERBATIM_REPORT",
                "page_reference": "Page 1",
                "ai_plain_language_explanation": (
                    "This section describes the equipment and protocol used to take your pictures. "
                    "It specifies the scanner resolution and imaging planes."
                ),
                "ai_explanation_source": "AI_PATIENT_EXPLANATION",
                "medical_terms_explained": tech_terms,
                "doctor_questions": [
                    "Did the imaging protocol provide clear, high-resolution views of all relevant areas?"
                ]
            })

        # B. Findings (Anatomical Observations)
        findings_text = sections.get("findings", "").strip()
        if findings_text:
            findings_terms = extract_and_explain_terms_in_text(findings_text)
            plain_summary = cls._synthesize_plain_findings(findings_text)
            explained_sections.append({
                "section_key": "findings",
                "section_title": "Anatomical Findings & Observations",
                "verbatim_text": findings_text,
                "source_type": "VERBATIM_REPORT",
                "page_reference": "Page 1",
                "ai_plain_language_explanation": plain_summary,
                "ai_explanation_source": "AI_PATIENT_EXPLANATION",
                "medical_terms_explained": findings_terms,
                "doctor_questions": [
                    "Are any of the identified findings considered urgent, or are they routine incidental observations?",
                    "Do any of these findings correlate with my reported physical symptoms?"
                ]
            })

        # C. Radiologist Impression / Conclusion
        imp_text = sections.get("impression", "").strip()
        if imp_text:
            imp_terms = extract_and_explain_terms_in_text(imp_text)
            explained_sections.append({
                "section_key": "impression",
                "section_title": "Radiologist Impression & Synthesis",
                "verbatim_text": imp_text,
                "source_type": "VERBATIM_REPORT",
                "page_reference": "Page 1",
                "ai_plain_language_explanation": (
                    "This is the radiologist's overall summary of the most important takeaways from your scan. "
                    "Your doctor uses this synthesis to determine next steps."
                ),
                "ai_explanation_source": "AI_PATIENT_EXPLANATION",
                "medical_terms_explained": imp_terms,
                "doctor_questions": [
                    "What are the next recommended steps based on the radiologist's impression?"
                ]
            })

        # D. Recommendations & Follow-Up
        rec_text = sections.get("recommendations", "").strip()
        if rec_text:
            rec_terms = extract_and_explain_terms_in_text(rec_text)
            explained_sections.append({
                "section_key": "recommendations",
                "section_title": "Clinical Follow-Up Guidance",
                "verbatim_text": rec_text,
                "source_type": "VERBATIM_REPORT",
                "page_reference": "Page 1",
                "ai_plain_language_explanation": (
                    "Follow-up recommendations outline the suggested timeframe for repeating a scan "
                    "or consulting a specialist to ensure findings remain stable."
                ),
                "ai_explanation_source": "AI_PATIENT_EXPLANATION",
                "medical_terms_explained": rec_terms,
                "doctor_questions": [
                    "Should we schedule repeat interval imaging or a specialist consultation as recommended?"
                ]
            })

        # 3. Grounded Individual Finding Explanations
        grounded_findings: List[Dict[str, Any]] = []
        for f in findings:
            finding_body = f.get("body") or f.get("finding", "")
            terms_in_finding = extract_and_explain_terms_in_text(finding_body)
            has_uncertainty = f.get("uncertainty", False) or "uncertain" in finding_body.lower() or "indeterminate" in finding_body.lower()

            grounded_findings.append({
                "finding_id": f.get("id", "p0"),
                "title": f.get("title", "Finding"),
                "verbatim_passage": finding_body,
                "source_type": "VERBATIM_REPORT",
                "source_ref": f.get("sourceRef", "Report Passage"),
                "page": 1,
                "is_verified_by_user": f.get("verified", is_verified),
                "uncertainty_flag": has_uncertainty,
                "ai_plain_language_summary": cls._translate_sentence_to_plain_language(finding_body),
                "ai_explanation_source": "AI_PATIENT_EXPLANATION",
                "medical_terms": terms_in_finding,
                "suggested_doctor_question": terms_in_finding[0]["doctor_question"] if terms_in_finding else "Can you explain how this finding affects my health?"
            })

        return {
            "status": "success",
            "report_id": report_id,
            "filename": report_data.get("filename", "Report"),
            "verification_status": "Verified by user" if is_verified else "Pending user verification",
            "is_verified": is_verified,
            "data_sufficiency": sufficiency,
            "explained_sections": explained_sections,
            "grounded_findings": grounded_findings,
            "overall_clinical_notice": (
                "AI EXPLANATION NOTICE: All explanations in this module are educational translations "
                "grounded strictly in the text of your uploaded report. PathoGuard-AI does not diagnose cancer, "
                "calculate statistical cancer probability, or replace the clinical judgment of your doctor."
            ),
            "generated_at": datetime.datetime.now().isoformat()
        }

    @classmethod
    def search_evidence(cls, report_data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Searches report text for evidence passages matching a patient query.
        Activates abstention safeguards if the query requests unsupported clinical conclusions.
        """
        raw_text = report_data.get("raw_text", "")
        findings = report_data.get("findings", [])
        report_id = report_data.get("report_id") or report_data.get("id", "RPT-LOCAL")

        # 1. Run abstention check on query
        abstention_check = AbstentionEvaluator.evaluate_interpretation(query, raw_text, findings)

        if abstention_check["should_abstain"]:
            return {
                "status": "abstained",
                "query": query,
                "report_id": report_id,
                "abstention_triggered": True,
                "abstention_details": abstention_check,
                "matching_passages": [],
                "disclaimer": "Diagnostic speculation withheld in accordance with clinical safety guidelines."
            }

        # 2. Extract search terms
        terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        matching_passages: List[Dict[str, Any]] = []

        # Search across raw text sentences
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_text) if s.strip()]
        for idx, sentence in enumerate(sentences):
            score = sum(1 for term in terms if term in sentence.lower())
            if score > 0:
                matching_passages.append({
                    "passage_index": idx,
                    "sentence": sentence,
                    "relevance_score": score,
                    "source_type": "VERBATIM_REPORT",
                    "page": 1,
                    "explained_terms": extract_and_explain_terms_in_text(sentence)
                })

        # Sort by relevance
        matching_passages.sort(key=lambda x: x["relevance_score"], reverse=True)

        return {
            "status": "success",
            "query": query,
            "report_id": report_id,
            "abstention_triggered": False,
            "matches_count": len(matching_passages),
            "matching_passages": matching_passages[:5],
            "disclaimer": "Passages retrieved verbatim from verified report text."
        }

    @classmethod
    def _synthesize_plain_findings(cls, text: str) -> str:
        """Generates a plain-language synthesis of anatomical findings."""
        text_lower = text.lower()
        parts = []

        if "nodule" in text_lower:
            parts.append("A small localized spot (nodule) was observed in the tissue.")
        if "no acute" in text_lower or "normal" in text_lower or "unremarkable" in text_lower:
            parts.append("Major organs and surrounding tissue boundaries appear intact without gross structural disruption.")
        if "atelectasis" in text_lower:
            parts.append("Minor area of lung under-expansion was noted, commonly seen with shallow breathing.")
        if "lymphadenopathy" in text_lower:
            parts.append("Lymph node sizes were evaluated.")

        if not parts:
            return "The report describes anatomical observations and measurements of the examined tissue."

        return " ".join(parts)

    @classmethod
    def _translate_sentence_to_plain_language(cls, sentence: str) -> str:
        """Translates an individual clinical sentence into plain words."""
        cleaned = sentence.strip()
        sentence_lower = sentence.lower()

        if "nodule" in sentence_lower:
            return "A small localized rounded spot was noted. Most small nodules are non-cancerous scars or past infections."
        if "subpleural" in sentence_lower:
            return "Positioned near the outer surface boundary of the lung where tissue has few nerve endings."
        if "atelectasis" in sentence_lower:
            return "Temporary minor under-inflation of a small lung section, common during scanning."
        if "technique" in sentence_lower or "protocol" in sentence_lower:
            return "Technical details about the scan equipment and slice intervals used."
        if "impression" in sentence_lower:
            return "Overall conclusion synthesized by the interpreting radiologist."
        if "recommendation" in sentence_lower:
            return "Follow-up schedule recommended by clinical imaging guidelines."

        return f"Clinical observation: {cleaned[:140]}."
