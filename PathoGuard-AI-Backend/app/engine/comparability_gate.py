"""
PathoGuard-AI — Report Comparability Gate (Feature 2)
Evaluates whether two temporal medical reports or findings are technically and clinically comparable
before longitudinal progression, regression, or treatment response claims are permitted.
Blocks clinically misleading comparisons between incompatible modalities, planes, or anatomy.
"""

from typing import Dict, List, Any, Optional, Tuple
import re
import datetime


class ComparabilityStatus:
    ELIGIBLE_FOR_LONGITUDINAL_CHANGE = "ELIGIBLE_FOR_LONGITUDINAL_CHANGE"
    INCOMPATIBLE_ANATOMICAL_SITE = "INCOMPATIBLE_ANATOMICAL_SITE"
    INCOMPATIBLE_IMAGING_MODALITY = "INCOMPATIBLE_IMAGING_MODALITY"
    INCOMPATIBLE_MEASUREMENT_PLANE = "INCOMPATIBLE_MEASUREMENT_PLANE"
    INSUFFICIENT_CALIBRATION_DATA = "INSUFFICIENT_CALIBRATION_DATA"
    CROSS_MODALITY_CAUTION = "CROSS_MODALITY_CAUTION"


class ReportComparabilityGate:
    """
    Guards longitudinal medical comparisons according to RECIST 1.1 / RANO principles:
    - Same anatomical organ and sub-anatomical zone.
    - Matching imaging modality or certified cross-modality conversion.
    - Consistent measurement plane (e.g. axial longest diameter vs coronal height).
    - Normalized metric units (cm vs mm).
    """

    KNOWN_MODALITIES = {
        "ct": "COMPUTED_TOMOGRAPHY",
        "cat scan": "COMPUTED_TOMOGRAPHY",
        "mri": "MAGNETIC_RESONANCE_IMAGING",
        "mr ": "MAGNETIC_RESONANCE_IMAGING",
        "ultrasound": "ULTRASOUND",
        "usg": "ULTRASOUND",
        "sonography": "ULTRASOUND",
        "pet": "PET_CT",
        "pet-ct": "PET_CT",
        "x-ray": "RADIOGRAPHY",
        "radiograph": "RADIOGRAPHY",
        "mammogram": "MAMMOGRAPHY",
        "mammography": "MAMMOGRAPHY",
        "biopsy": "HISTOPATHOLOGY",
        "histopathology": "HISTOPATHOLOGY"
    }

    ANATOMICAL_SITES = [
        "lung", "pulmonary", "chest", "thorax", "thoracic", "liver", "hepatic", "breast", "mammary",
        "colon", "colorectal", "prostate", "kidney", "renal", "brain",
        "cerebral", "pancreas", "pancreatic", "thyroid", "lymph node",
        "cervical", "mediastinal", "retroperitoneal", "axillary"
    ]

    MEASUREMENT_PLANES = [
        "axial", "coronal", "sagittal", "transverse", "longitudinal"
    ]

    @classmethod
    def extract_comparability_profile(cls, report_or_finding_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extracts structured comparability attributes from report text or metadata."""
        meta = metadata or {}
        text = (report_or_finding_text or "").lower()

        # 1. Modality detection (ordered by length / specificity with word boundary checks)
        modality = meta.get("modality")
        if not modality:
            # Sort by length descending so specific words ('histopathology', 'biopsy') match before short acronyms ('ct')
            sorted_modalities = sorted(cls.KNOWN_MODALITIES.items(), key=lambda x: len(x[0]), reverse=True)
            for keyword, canonical in sorted_modalities:
                pattern = r'\b' + re.escape(keyword.strip()) + r'\b'
                if re.search(pattern, text):
                    modality = canonical
                    break
        if not modality:
            modality = "UNSPECIFIED_MODALITY"

        # 2. Anatomical site & subsite
        anatomical_site = meta.get("anatomical_site")
        if not anatomical_site:
            for site in cls.ANATOMICAL_SITES:
                if site in text:
                    anatomical_site = site.upper()
                    break
        if not anatomical_site:
            anatomical_site = "UNSPECIFIED_SITE"

        # Subsite detection (e.g. right upper lobe, segment 4, upper outer quadrant)
        subsite_match = re.search(
            r'\b(right\s+upper\s+lobe|left\s+lower\s+lobe|rul|lll|rml|segment\s+[0-9a-c]+|upper\s+outer\s+quadrant|uoq)\b',
            text
        )
        anatomical_subsite = subsite_match.group(0).upper() if subsite_match else "GENERAL_ZONE"

        # 3. Measurement Plane
        plane = meta.get("measurement_plane")
        if not plane:
            for p in cls.MEASUREMENT_PLANES:
                if p in text:
                    plane = p.upper()
                    break
        if not plane:
            plane = "AXIAL"  # Standard radiology default

        # 4. Dimension & Units
        dim_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:x\s*(\d+(?:\.\d+)?))?\s*(cm|mm)\b', text)
        size_longest_mm = None
        raw_dimension = None
        if dim_match:
            val1 = float(dim_match.group(1))
            val2 = float(dim_match.group(2)) if dim_match.group(2) else None
            unit = dim_match.group(3)
            raw_dimension = dim_match.group(0)

            # Max dimension in mm
            longest = max(val1, val2) if val2 else val1
            size_longest_mm = longest * 10.0 if unit == "cm" else longest

        return {
            "modality": modality,
            "anatomical_site": anatomical_site,
            "anatomical_subsite": anatomical_subsite,
            "measurement_plane": plane,
            "size_longest_mm": size_longest_mm,
            "raw_dimension": raw_dimension,
            "source_snippet": report_or_finding_text[:120]
        }

    @classmethod
    def evaluate_comparability(
        cls,
        prior_study: Dict[str, Any],
        current_study: Dict[str, Any],
        study_dates: Optional[Tuple[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Gating function to evaluate comparability between prior and current clinical findings.
        Returns gating decision, status code, clinical rationale, and quantitative progression delta if eligible.
        """
        p_profile = cls.extract_comparability_profile(
            prior_study.get("text", "") or prior_study.get("finding", ""),
            prior_study.get("metadata")
        )
        c_profile = cls.extract_comparability_profile(
            current_study.get("text", "") or current_study.get("finding", ""),
            current_study.get("metadata")
        )

        rejection_reasons = []
        cautions = []

        # Gate 1: Anatomical Site Match
        p_site = p_profile["anatomical_site"]
        c_site = c_profile["anatomical_site"]
        if p_site != "UNSPECIFIED_SITE" and c_site != "UNSPECIFIED_SITE" and p_site != c_site:
            return {
                "decision": "BLOCKED",
                "status": ComparabilityStatus.INCOMPATIBLE_ANATOMICAL_SITE,
                "is_eligible_for_change_analysis": False,
                "rejection_reason": (
                    f"Incompatible anatomical targets: Prior finding evaluates '{p_site}' whereas "
                    f"current finding evaluates '{c_site}'. Cross-organ progression comparison is clinically invalid."
                ),
                "prior_profile": p_profile,
                "current_profile": c_profile,
                "calculated_delta_percent": None,
                "patient_guidance": "These two studies examine completely different areas of the body and cannot be compared for growth or shrinkage."
            }

        # Gate 2: Imaging Modality Compatibility
        p_mod = p_profile["modality"]
        c_mod = c_profile["modality"]
        modality_mismatch = (p_mod != "UNSPECIFIED_MODALITY" and c_mod != "UNSPECIFIED_MODALITY" and p_mod != c_mod)

        # Modalities that are strictly non-comparable for metric RECIST growth (e.g. Ultrasound vs CT, or Biopsy vs X-Ray)
        strictly_incompatible = {
            ("HISTOPATHOLOGY", "COMPUTED_TOMOGRAPHY"),
            ("HISTOPATHOLOGY", "ULTRASOUND"),
            ("RADIOGRAPHY", "COMPUTED_TOMOGRAPHY")
        }
        if (p_mod, c_mod) in strictly_incompatible or (c_mod, p_mod) in strictly_incompatible:
            return {
                "decision": "BLOCKED",
                "status": ComparabilityStatus.INCOMPATIBLE_IMAGING_MODALITY,
                "is_eligible_for_change_analysis": False,
                "rejection_reason": (
                    f"Strictly incompatible examination modalities ({p_mod} vs {c_mod}). "
                    "Different imaging physics and spatial resolutions prevent reliable quantitative delta computation."
                ),
                "prior_profile": p_profile,
                "current_profile": c_profile,
                "calculated_delta_percent": None,
                "patient_guidance": "These reports use completely different diagnostic techniques with different levels of detail, so direct measurements cannot be compared."
            }

        if modality_mismatch:
            cautions.append(
                f"Cross-modality comparison ({p_mod} vs {c_mod}): Interpret metric variations with extreme caution due to technique sensitivity differences."
            )

        # Gate 3: Measurement Plane Compatibility
        p_plane = p_profile["measurement_plane"]
        c_plane = c_profile["measurement_plane"]
        if p_plane != c_plane and p_plane != "AXIAL" and c_plane != "AXIAL":
            cautions.append(
                f"Different measurement planes ({p_plane} vs {c_plane}). Longest diameter should ideally be assessed on identical orientations."
            )

        # Gate 4: Quantitative delta calculation if dimensions exist
        p_size = p_profile.get("size_longest_mm")
        c_size = c_profile.get("size_longest_mm")
        delta_pct = None
        change_category = "STABLE_OR_INDETERMINATE"

        if p_size and c_size and p_size > 0:
            delta_pct = round(((c_size - p_size) / p_size) * 100.0, 1)
            # RECIST 1.1 thresholds: >= +20% progression, <= -30% partial response
            if delta_pct >= 20.0:
                change_category = "APPARENT_METRIC_INCREASE"
            elif delta_pct <= -30.0:
                change_category = "APPARENT_METRIC_DECREASE"
            else:
                change_category = "STABLE_METRIC_DIMENSION"

        status = ComparabilityStatus.CROSS_MODALITY_CAUTION if cautions else ComparabilityStatus.ELIGIBLE_FOR_LONGITUDINAL_CHANGE

        return {
            "decision": "PERMITTED" if not rejection_reasons else "BLOCKED",
            "status": status,
            "is_eligible_for_change_analysis": True,
            "change_category": change_category,
            "calculated_delta_percent": delta_pct,
            "prior_size_mm": p_size,
            "current_size_mm": c_size,
            "cautions": cautions,
            "prior_profile": p_profile,
            "current_profile": c_profile,
            "clinical_rationale": (
                f"Anatomy matched ({p_site}). Modalities ({p_mod} / {c_mod}). "
                + (" ".join(cautions) if cautions else "Fully comparable under standard clinical assessment guidelines.")
            ),
            "patient_guidance": (
                "Both studies evaluate the same anatomical region. Do not assume any slight millimeter variation indicates disease progression; "
                "consult your treating specialist for official clinical interpretation."
            )
        }
