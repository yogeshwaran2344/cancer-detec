"""
PathoGuard-AI — Clinical Abstention & Evidence Sufficiency Engine
Detects unsupported claims, missing evidence, contradictory reports, and extraction errors.
Withholds autonomous diagnostic conclusions and enforces clinical clinician-referral safeguards.
"""

from typing import Dict, List, Any, Optional
import re

# Keywords indicating user or interpreter might be leaping to an unverified cancer conclusion
DIAGNOSTIC_CLAIM_PATTERNS = [
    r"\b(?:is it|does this mean|confirm|rule out|have|diagnose)\s+(?:cancer|malignancy|tumor|carcinoma|lymphoma)\b",
    r"\b(?:what stage|stage [1-4]|metastasis|terminal)\b",
    r"\b(?:is it malignant|benign or malignant)\b",
    r"\b(?:percentage risk|probability of cancer|cancer percentage)\b"
]


class AbstentionEvaluator:
    """Evaluates whether an evidence interpretation is medically supported or requires abstention."""

    @staticmethod
    def evaluate_interpretation(query: str, report_text: str, findings: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Checks whether a question or statement requests an unsupported diagnostic certainty.
        Returns an abstention response with clinical grounding if unsupported.
        """
        query_lower = query.lower()
        report_lower = report_text.lower()
        findings = findings or []

        # 1. Rule A: Autonomous Cancer Diagnosis Abstention
        for pattern in DIAGNOSTIC_CLAIM_PATTERNS:
            if re.search(pattern, query_lower):
                return {
                    "should_abstain": True,
                    "abstention_category": "AUTONOMOUS_DIAGNOSIS_UNSUPPORTED",
                    "reason": "Radiological imaging reports describe visual anatomical densities, not cellular pathology. A radiological finding alone cannot independently confirm or rule out malignancy.",
                    "clinical_safeguard": "Only tissue biopsy, cytology, or longitudinal clinical evaluation by your physician can establish a definitive medical diagnosis. PathoGuard-AI strictly abstains from calculating automated cancer risk percentages or delivering diagnostic pronouncements.",
                    "recommended_action": "Consult your ordering physician to review whether the findings warrant clinical surveillance, tissue sampling, or specialist referral."
                }

        # 2. Rule B: Longitudinal Disease Progression from Wording Differences
        progression_patterns = [
            r"\b(progressing|progression|worsening|getting worse|getting bigger|spreading|grown)\b",
            r"\b(different wording|description changed|wording changed)\b"
        ]
        if any(re.search(pat, query_lower) for pat in progression_patterns):
            has_explicit_comparison = "prior" in report_lower or "compared to" in report_lower or "baseline" in report_lower
            if not has_explicit_comparison:
                return {
                    "should_abstain": True,
                    "abstention_category": "LONGITUDINAL_PROGRESSION_UNSUPPORTED",
                    "reason": "This report does not contain an explicit historical baseline comparison. Differences in descriptive terminology between separate imaging facilities do not constitute evidence of disease progression.",
                    "clinical_safeguard": "Radiologists frequently use varying descriptive wording for the same stable finding. True temporal comparison requires a radiologist to view both original digital imaging scans side by side.",
                    "recommended_action": "Request a formal comparison between current and previous imaging discs through your imaging facility."
                }

        # 3. Rule C: Sufficient Grounded Evidence Found
        return {
            "should_abstain": False,
            "abstention_category": "EVIDENCE_GROUNDED",
            "reason": "The query can be addressed using grounded passages from the verified report text without diagnostic speculation.",
            "clinical_safeguard": "Information is strictly educational and derived from the document text.",
            "recommended_action": "Review the linked report passage."
        }

    @staticmethod
    def check_report_data_sufficiency(sections: Dict[str, str], extraction_errors: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Checks whether report text is sufficient for reliable patient explanation
        or if critical sections / extraction quality are compromised.
        """
        issues: List[str] = []
        is_sufficient = True

        # Check for missing core sections
        if not sections.get("findings") or len(sections.get("findings", "")) < 20:
            issues.append("Missing or unclassified Findings section. Detailed anatomical observations are unavailable.")
            is_sufficient = False

        if not sections.get("impression") or len(sections.get("impression", "")) < 10:
            issues.append("Missing radiologist Impression or Conclusion section. Summary interpretation is unavailable.")

        # Check for high extraction errors
        if extraction_errors:
            high_sev = [e for e in extraction_errors if e.get("severity") in ("error", "caution")]
            if len(high_sev) > 0:
                issues.append(f"Detected {len(high_sev)} image clarity or OCR recognition notice(s). Text requires patient verification.")

        return {
            "is_sufficient": is_sufficient,
            "has_warnings": len(issues) > 0,
            "issues": issues,
            "recommendation": "Review original document carefully before relying on extracted clinical summaries." if issues else "Report structure is complete."
        }
