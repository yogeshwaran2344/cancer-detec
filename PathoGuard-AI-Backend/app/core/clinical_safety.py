"""
Context-Aware Clinical Safety & Triage Pathway
Replaces naive substring keyword matching with context-aware evaluation
handling negation (e.g., 'denies hemoptysis'), temporality (e.g., '5 years ago resolved'),
and severity distinctions.

NOTE: This module implements safety screening decision support heuristics.
It is NOT an autonomous medical device or complete emergency department triage system.
"""

import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


# Acute Red Flag Definitions with Synonyms and Anatomical Targets
ACUTE_RED_FLAGS: Dict[str, Dict[str, Any]] = {
    "hemoptysis": {
        "canonical": "Hemoptysis (Coughing blood)",
        "patterns": [
            r"\bhemoptysis\b",
            r"\bcoughing\s+(?:up\s+)?(?:blood|red\s+sputum|frank\s+blood)\b",
            r"\bblood(?:-stained|\s+streaked)?\s+sputum\b",
            r"\bspitting\s+blood\b"
        ],
        "category": "PULMONARY_ACUTE",
        "guidance": "Requires immediate evaluation to rule out active bronchial bleeding or vascular erosion."
    },
    "rectal_bleeding": {
        "canonical": "Lower GI Bleeding / Melena",
        "patterns": [
            r"\bhematochezia\b",
            r"\bmelena\b",
            r"\brectal\s+bleeding\b",
            r"\bblood\s+(?:in|on)\s+(?:the\s+)?stool\b",
            r"\bblack\s+tarry\s+stool\b"
        ],
        "category": "GI_ACUTE",
        "guidance": "Requires clinical workup for gastrointestinal lesion or acute hemorrhage."
    },
    "unexplained_weight_loss": {
        "canonical": "Rapid Unintentional Weight Loss",
        "patterns": [
            r"\bunintentional\s+weight\s+loss\b",
            r"\bunexplained\s+weight\s+loss\b",
            r"\blost\s+\d+\s*(?:kg|lbs|pounds)\s+(?:without\s+trying|unintentionally)\b",
            r"\brapid\s+wasting\b"
        ],
        "category": "CONSTITUTIONAL_SYSTEMIC",
        "guidance": "Significant unintentional loss warrants metabolic and oncologic baseline screening."
    },
    "dysphagia": {
        "canonical": "Dysphagia (Difficulty swallowing)",
        "patterns": [
            r"\bdysphagia\b",
            r"\bdifficulty\s+swallowing\b",
            r"\bfood\s+(?:sticking|getting\s+stuck)\s+(?:in\s+throat|in\s+esophagus)\b",
            r"\bpainful\s+swallowing\b"
        ],
        "category": "ESOPHAGEAL_AERODIGESTIVE",
        "guidance": "Progressive difficulty swallowing solids warrants barium swallow or endoscopic inspection."
    },
    "fixed_breast_lump": {
        "canonical": "Palpable Fixed/Painless Mass",
        "patterns": [
            r"\bhard\s+fixed\s+(?:breast\s+)?(?:lump|mass)\b",
            r"\bpainless\s+breast\s+(?:lump|mass)\b",
            r"\bimpalpable\s+fixed\s+nodule\b"
        ],
        "category": "PALPABLE_MASS",
        "guidance": "Non-tender, non-mobile masses require diagnostic mammography/ultrasound correlation."
    },
    "jaundice": {
        "canonical": "Jaundice / Hyperbilirubinemia Signs",
        "patterns": [
            r"\bjaundice\b",
            r"\bicterus\b",
            r"\byellow(?:ing)?\s+(?:of\s+)?(?:the\s+)?(?:skin|eyes|sclera)\b"
        ],
        "category": "HEPATOBILIARY_ACUTE",
        "guidance": "Jaundice indicates biliary obstruction or hepatic decompensation requiring prompt labs."
    },
    "severe_respiratory_distress": {
        "canonical": "Acute / Severe Respiratory Distress",
        "patterns": [
            r"\bstridor\b",
            r"\bsevere\s+(?:shortness\s+of\s+breath|dyspnea)\b",
            r"\bgasping\s+for\s+air\b",
            r"\binability\s+to\s+breathe\b"
        ],
        "category": "AIRWAY_EMERGENCY",
        "guidance": "Severe shortness of breath requires emergency department clinical triage."
    }
}

# Negation scope patterns
NEGATION_PRE_PATTERNS = [
    r"\bdenies\b",
    r"\bno\b",
    r"\bnever\s+had\b",
    r"\bnegative\s+for\b",
    r"\bwithout\b",
    r"\babsence\s+of\b",
    r"\bnot\s+experiencing\b",
    r"\bdenied\b",
    r"\bfree\s+of\b",
    r"\brules?\s+out\b"
]

# Historical / Remote temporality patterns
HISTORICAL_PATTERNS = [
    r"\b\d+\s+years?\s+ago\b",
    r"\bhistory\s+of\s+(?:childhood\s+)?",
    r"\bpast\s+medical\s+history\b",
    r"\bresolved\b",
    r"\btreated\s+in\s+\d{4}\b",
    r"\bno\s+longer\s+present\b",
    r"\bpreviously\s+cured\b"
]


@dataclass
class ClinicalSafetyEvaluation:
    is_urgent: bool
    triage_category: str
    active_red_flags: List[str] = field(default_factory=list)
    negated_findings: List[str] = field(default_factory=list)
    historical_findings: List[str] = field(default_factory=list)
    clinical_guidance: List[str] = field(default_factory=list)
    evaluation_summary: str = ""
    disclaimer: str = (
        "CRITICAL CLINICAL NOTICE: PathoGuard-AI is an informational decision-support tool. "
        "It DOES NOT diagnose cancer, DOES NOT rule out malignancy, and DOES NOT calculate quantitative risk scores. "
        "Always consult a qualified physician for clinical evaluation."
    )


def evaluate_clinical_safety(
    symptoms: List[str],
    patient_note: Optional[str] = None
) -> ClinicalSafetyEvaluation:
    """
    Evaluates symptoms and patient notes with context-aware negation and temporality handling.
    
    Prevents false alarms on phrases like:
    - 'Patient denies hemoptysis' -> NEGATED, no red flag alert
    - 'No blood in stool' -> NEGATED, no red flag alert
    - 'History of jaundice 10 years ago, resolved' -> HISTORICAL, no acute alert
    
    Accurately flags genuine acute emergency signs:
    - 'Coughing up frank blood since yesterday' -> ACUTE_RED_FLAG
    """
    combined_elements = list(symptoms)
    if patient_note:
        combined_elements.append(patient_note)
    
    full_text = " . ".join(combined_elements)
    
    # Split text into sentence/clause segments for bounded negation scope
    clauses = re.split(r'[.,;!\n]+', full_text)
    
    active_flags: List[str] = []
    negated_flags: List[str] = []
    historical_flags: List[str] = []
    guidance_notes: List[str] = []
    
    for clause in clauses:
        clean_clause = clause.strip().lower()
        if not clean_clause:
            continue
            
        for flag_key, flag_meta in ACUTE_RED_FLAGS.items():
            # Check if any synonym matches this clause
            matched_pattern = False
            match_start = -1
            match_end = -1
            for pat in flag_meta["patterns"]:
                m = re.search(pat, clean_clause)
                if m:
                    matched_pattern = True
                    match_start = m.start()
                    match_end = m.end()
                    break
            
            if not matched_pattern:
                continue
                
            # Check negation in preceding text of this clause
            preceding_text = clean_clause[:match_start]
            is_negated = any(re.search(neg, preceding_text) for neg in NEGATION_PRE_PATTERNS)
            
            # Check historical context
            is_historical = any(re.search(hist, clean_clause) for hist in HISTORICAL_PATTERNS)
            
            flag_name = flag_meta["canonical"]
            
            if is_negated:
                if flag_name not in negated_flags:
                    negated_flags.append(flag_name)
            elif is_historical:
                if flag_name not in historical_flags:
                    historical_flags.append(flag_name)
            else:
                if flag_name not in active_flags:
                    active_flags.append(flag_name)
                    guidance_notes.append(f"{flag_name}: {flag_meta['guidance']}")

    # Determine overall triage state
    if active_flags:
        is_urgent = True
        triage_cat = "ACUTE_WARNING_SIGNS_DETECTED"
        summary = (
            f"Active warning sign(s) detected: {', '.join(active_flags)}. "
            "Prompt in-person clinical evaluation is recommended."
        )
    elif negated_flags or historical_flags:
        is_urgent = False
        triage_cat = "RESOLVED_OR_DENIED_SYMPTOMS"
        parts = []
        if negated_flags:
            parts.append(f"Patient explicitly denies: {', '.join(negated_flags)}")
        if historical_flags:
            parts.append(f"Historical/resolved context noted: {', '.join(historical_flags)}")
        summary = "; ".join(parts) + ". No acute red flags active."
    else:
        is_urgent = False
        triage_cat = "ROUTINE_SYMPTOM_PRESENTATION"
        summary = "No acute red-flag warning signs identified in reported context."
        
    return ClinicalSafetyEvaluation(
        is_urgent=is_urgent,
        triage_category=triage_cat,
        active_red_flags=active_flags,
        negated_findings=negated_flags,
        historical_findings=historical_flags,
        clinical_guidance=guidance_notes,
        evaluation_summary=summary
    )
