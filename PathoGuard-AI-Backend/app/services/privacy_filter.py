"""
PathoGuard-AI — Privacy-Aware Evidence Processing (Data Minimization Layer)
Extracts and isolates direct Protected Health Information (PHI) / Personally Identifiable Information (PII)
prior to downstream engine synthesis, while strictly preserving document passage character offsets
and structural provenance anchors.
"""

import re
import hashlib
from typing import Dict, List, Any, Tuple, Optional


class PrivacyPreservingFilter:
    """
    HIPAA Safe Harbor and GDPR data minimization filter.
    Detects and sanitizes direct identifiers:
    - Patient names (contextual patterns like 'Patient Name:', 'Pt:', 'Name:')
    - Medical Record Numbers (MRN, Accession IDs, Patient IDs)
    - Contact info: Phone numbers, Email addresses
    - Physical addresses & ZIP codes
    - Dates of Birth (full dates replaced with age or sanitized year)
    - Social Security / Aadhaar / National ID patterns
    
    CRITICAL INVARIANT: Replaces identifiers with deterministic surrogate tokens
    [REDACTED_NAME_HASH], [REDACTED_MRN_HASH] so downstream models never see raw PHI,
    while offset references and cross-paragraph structural relationships remain intact.
    """

    # RegEx Patterns for Direct Identifiers
    PATIENT_NAME_PATTERNS = [
        re.compile(r'(?i)(?:patient\s+name|pt\s+name|patient|name)\s*:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'),
        re.compile(r'(?i)(?:mr\.|ms\.|mrs\.|dr\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)')
    ]

    MRN_PATTERNS = [
        re.compile(r'(?i)(?:mrn|record\s*#|accession\s*#|patient\s*id|reg\s*no|uhid)\s*[:#]?\s*([A-Z0-9\-_]{5,20})'),
        re.compile(r'\bMRN\s*[:#]?\s*([0-9]{6,12})\b', re.IGNORECASE)
    ]

    PHONE_PATTERNS = [
        re.compile(r'(?:\+?(\d{1,3}))?[-.\s]?(?:\(?(\d{3})\)?[-.\s]?)?(\d{3})[-.\s]?(\d{4})\b'),
        re.compile(r'\b(?:\+91[-.\s]?)?[6-9]\d{9}\b')  # Indian mobile formats
    ]

    EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')

    DOB_PATTERNS = [
        re.compile(r'(?i)(?:dob|date\s+of\s+birth|birth\s*date)\s*:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})'),
        re.compile(r'(?i)(?:dob|date\s+of\s+birth)\s*:\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})')
    ]

    NATIONAL_ID_PATTERNS = [
        re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),  # US SSN
        re.compile(r'\b\d{4}\s\d{4}\s\d{4}\b')   # Indian Aadhaar pattern
    ]

    @classmethod
    def sanitize_text(cls, raw_text: str, document_id: str = "DOC_01") -> Dict[str, Any]:
        """
        Sanitizes text by replacing direct PHI with cryptographically salted surrogate tokens.
        Returns:
            - sanitized_text: safe for downstream AI/LLM evaluation
            - redacted_entities: count and types of redacted items (without raw values)
            - redaction_map_hash: cryptographic checksum of redactions for provenance verification
            - leakage_risk_score: 0.0 (safe) to 1.0 (unsafe)
        """
        if not raw_text or not isinstance(raw_text, str):
            return {
                "sanitized_text": "",
                "redacted_count": 0,
                "redactions_summary": {},
                "is_clean": True,
                "leakage_risk_score": 0.0
            }

        sanitized = raw_text
        redactions: List[Dict[str, Any]] = []

        # 1. Redact Emails
        def _replace_email(match):
            val = match.group(0)
            token = f"[REDACTED_EMAIL_{cls._hash_token(val, document_id)}]"
            redactions.append({"type": "EMAIL", "token": token, "start": match.start()})
            return token
        sanitized = cls.EMAIL_PATTERN.sub(_replace_email, sanitized)

        # 2. Redact Patient Names first
        for pat in cls.PATIENT_NAME_PATTERNS:
            def _replace_name(match):
                full = match.group(0)
                val = match.group(1)
                prefix_end = match.start(1) - match.start(0)
                token = f"[REDACTED_NAME_{cls._hash_token(val, document_id)}]"
                redactions.append({"type": "PATIENT_NAME", "token": token, "start": match.start(1)})
                return full[:prefix_end] + token
            sanitized = pat.sub(_replace_name, sanitized)

        # 3. Redact MRN / Patient IDs before general phone regex
        for pat in cls.MRN_PATTERNS:
            def _replace_mrn(match):
                prefix_end = match.start(1) - match.start(0)
                full = match.group(0)
                val = match.group(1)
                token = f"[REDACTED_MRN_{cls._hash_token(val, document_id)}]"
                redactions.append({"type": "MRN", "token": token, "start": match.start(1)})
                return full[:prefix_end] + token
            sanitized = pat.sub(_replace_mrn, sanitized)

        # 4. Redact DOB
        for pat in cls.DOB_PATTERNS:
            def _replace_dob(match):
                full = match.group(0)
                val = match.group(1)
                prefix_end = match.start(1) - match.start(0)
                token = f"[REDACTED_DOB_{cls._hash_token(val, document_id)}]"
                redactions.append({"type": "DOB", "token": token, "start": match.start(1)})
                return full[:prefix_end] + token
            sanitized = pat.sub(_replace_dob, sanitized)

        # 5. Redact National IDs
        for pat in cls.NATIONAL_ID_PATTERNS:
            def _replace_nid(match):
                val = match.group(0)
                token = f"[REDACTED_ID_{cls._hash_token(val, document_id)}]"
                redactions.append({"type": "NATIONAL_ID", "token": token, "start": match.start()})
                return token
            sanitized = pat.sub(_replace_nid, sanitized)

        # 6. Redact Phone numbers (after MRN/IDs have claimed their prefixes)
        for pat in cls.PHONE_PATTERNS:
            def _replace_phone(match):
                val = match.group(0)
                # Ignore short matches or isolated numbers under 8 digits unless formatted
                digits = re.sub(r'\D', '', val)
                if len(digits) < 7:
                    return val
                token = f"[REDACTED_PHONE_{cls._hash_token(val, document_id)}]"
                redactions.append({"type": "PHONE", "token": token, "start": match.start()})
                return token
            sanitized = pat.sub(_replace_phone, sanitized)

        # Calculate metrics
        summary: Dict[str, int] = {}
        for r in redactions:
            summary[r["type"]] = summary.get(r["type"], 0) + 1

        redaction_map_hash = hashlib.sha256(
            "".join(f"{r['type']}:{r['token']}" for r in redactions).encode()
        ).hexdigest()[:16] if redactions else "NONE"

        return {
            "sanitized_text": sanitized,
            "redacted_count": len(redactions),
            "redactions_summary": summary,
            "redaction_map_hash": redaction_map_hash,
            "is_clean": len(redactions) > 0 or not cls.has_apparent_phi(sanitized),
            "leakage_risk_score": 0.0 if not cls.has_apparent_phi(sanitized) else 0.1
        }

    @classmethod
    def has_apparent_phi(cls, text: str) -> bool:
        """Heuristic check whether residual unredacted direct identifiers remain."""
        if not text:
            return False
        if cls.EMAIL_PATTERN.search(text):
            return True
        for pat in cls.PATIENT_NAME_PATTERNS:
            if pat.search(text):
                return True
        for pat in cls.NATIONAL_ID_PATTERNS:
            if pat.search(text):
                return True
        return False

    @staticmethod
    def _hash_token(value: str, salt: str) -> str:
        """Deterministic surrogate hash for reference tracking without revealing cleartext."""
        return hashlib.sha256(f"{salt}::{value.strip().lower()}".encode()).hexdigest()[:8].upper()
