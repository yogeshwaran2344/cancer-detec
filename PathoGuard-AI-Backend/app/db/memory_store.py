"""
In-Memory Store for Local Clinical Development Sandbox
Preserves assessments and parsed reports during session lifecycle without external database dependency.
"""

from typing import Dict, List, Any
import datetime

ASSESSMENTS_STORE: Dict[str, Dict[str, Any]] = {
    "ASM-2026-0941": {
        "id": "ASM-2026-0941",
        "date": "2026-10-18T14:32:00",
        "type": "Combined Assessment",
        "status": "Assessment summary ready",
        "summary": "Thoracic scan report reconciled with progressive dry cough and dyspnea.",
        "findings_count": 4,
        "report_linked": True,
        "patient_reported": {
            "primary_symptoms": ["Persistent dry cough", "Progressive dyspnea on exertion"],
            "onset": "4-6 weeks",
            "trajectory": "Worsening",
            "frequency": "Daily",
            "age_bracket": "45-54",
            "medical_history": ["Seasonal allergies"]
        },
        "report_findings": [
            {
                "id": "p0",
                "title": "Protocol & Modality",
                "finding": "High-resolution thoracic CT without contrast.",
                "body": "Helical acquisition from thoracic inlet to diaphragm.",
                "section": "technique",
                "anchor": "p0",
                "verified": True
            },
            {
                "id": "p1",
                "title": "Subpleural Reticular Markings",
                "finding": "Mild peripheral reticular markings; no discrete pulmonary mass.",
                "body": "Subpleural parenchymal architecture shows mild bibasilar interstitial thickening.",
                "section": "findings",
                "anchor": "p1",
                "verified": True
            }
        ],
        "missing_or_conflicting": [
            {
                "finding_id": "p1",
                "category": "missing_or_conflicting",
                "title": "Symptom Duration vs. Radiographic Finding",
                "description": "Patient reports worsening dyspnea over 6 weeks; report shows only mild chronic-appearing baseline interstitial change.",
                "clinical_note": "Does not exclude early inflammatory or reactive process. Clinical correlation required."
            }
        ],
        "suggested_next_steps": [
            "Share summary with your pulmonologist or primary physician.",
            "Ask doctor whether pulmonary function testing (spirometry) is indicated.",
            "Seek immediate urgent review if you develop hemoptysis, severe chest pain, or sudden shortness of breath."
        ],
        "red_flag_alert": False
    },
    "ASM-2026-0812": {
        "id": "ASM-2026-0812",
        "date": "2026-10-12T09:15:00",
        "type": "Symptom Questionnaire",
        "status": "Assessment summary ready",
        "summary": "Localized left flank soreness following exertion; no scan uploaded.",
        "findings_count": 1,
        "report_linked": False,
        "patient_reported": {
            "primary_symptoms": ["Intermittent flank soreness"],
            "onset": "1-2 weeks",
            "trajectory": "Stable",
            "frequency": "After physical activity"
        },
        "report_findings": [],
        "missing_or_conflicting": [],
        "suggested_next_steps": [
            "Monitor trajectory over 14 days.",
            "Consult primary care provider if pain persists or changes in quality."
        ],
        "red_flag_alert": False
    }
}

REPORTS_STORE: Dict[str, Dict[str, Any]] = {}
