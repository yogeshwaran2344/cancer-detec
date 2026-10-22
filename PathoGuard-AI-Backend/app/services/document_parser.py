"""
PathoGuard-AI — Clinical Report Document Parser, OCR Engine & Section Classifier
Provides local privacy-preserving digital PDF extraction, genuine text parsing,
defensible extraction quality evaluation, section segmentation, and page-anchored findings.

CRITICAL CLINICAL INTEGRITY RULE:
Never generates synthetic, placeholder, or simulated clinical findings.
If extraction fails or no text is detected, reports the failure honestly.
"""

import io
import re
import shutil
import subprocess
from typing import Dict, Any, List, Optional
import datetime

COMMON_CLINICAL_TERMS = {
    "examination", "technique", "findings", "impression", "recommendation", "recommendations",
    "protocol", "contrast", "axial", "coronal", "sagittal", "computed", "tomography", "ct",
    "mri", "magnetic", "resonance", "ultrasound", "radiograph", "x-ray", "imaging", "scan",
    "nodule", "mass", "lesion", "density", "opacity", "infiltrate", "effusion", "consolidation",
    "lymph", "nodes", "mediastinum", "pleural", "subpleural", "spiculated", "calcification",
    "attenuation", "enhancement", "bilateral", "unremarkable", "normal", "intact", "without",
    "evidence", "acute", "chronic", "mild", "moderate", "severe", "stable", "interval", "change",
    "prior", "baseline", "study", "comparison", "patient", "clinical", "history", "indication",
    "follow-up", "biopsy", "correlation", "correlate", "pulmonary", "thoracic", "pelvic", "hepatic",
    "evaluation", "evaluated", "limits", "within", "demonstrates", "visualized", "observed"
}


def calculate_extraction_quality(raw_text: str, pages_data: List[Dict[str, Any]]) -> float:
    """
    Computes a defensible, multi-factor extraction quality assessment (0.0% to 100.0%)
    based on character validity, lexical coherence, section presence, and page density.
    Never returns hardcoded or invented values.
    """
    clean_text = raw_text.strip()
    if not clean_text or len(clean_text) < 15:
        return 0.0

    # Factor 1: Character validity (ratio of standard alphanumeric & punctuation to total characters)
    printable_chars = sum(1 for c in clean_text if c.isalnum() or c in ' .,;:()[]-/\n\r\t%"\'<>=+*#&')
    char_validity = printable_chars / max(len(clean_text), 1)

    # Factor 2: Lexical coherence (ratio of recognized English / clinical words)
    words = re.findall(r'[a-zA-Z]{2,}', clean_text.lower())
    if not words:
        return 0.0

    recognized_words = sum(1 for w in words if w in COMMON_CLINICAL_TERMS or len(w) >= 4)
    lexical_ratio = recognized_words / max(len(words), 1)

    # Factor 3: Clinical structure markers (presence of key diagnostic headings)
    headings = ["TECHNIQUE", "EXAMINATION", "FINDINGS", "IMPRESSION", "RECOMMENDATION", "HISTORY", "INDICATION", "OBSERVATIONS"]
    upper_text = clean_text.upper()
    found_headings = sum(1 for h in headings if h in upper_text)
    structural_score = min(found_headings / 3.0, 1.0)

    # Factor 4: Density & completeness across pages
    total_chars = sum(p.get("char_count", len(p.get("text", ""))) for p in pages_data) if pages_data else len(clean_text)
    avg_page_chars = total_chars / max(len(pages_data), 1)
    density_score = min(avg_page_chars / 150.0, 1.0)

    # Composite weighted formula
    quality = (char_validity * 30.0) + (lexical_ratio * 35.0) + (structural_score * 25.0) + (density_score * 10.0)
    return round(min(max(quality, 0.0), 100.0), 1)


def try_ocr_image(content: bytes) -> Optional[str]:
    """
    Attempts genuine Optical Character Recognition on image bytes.
    1. Tries pytesseract library if available.
    2. Tries standard tesseract executable via subprocess.
    3. Never fabricates clinical text from metadata or image dimensions.
    Returns recognized text string or None.
    """
    # Attempt 1: pytesseract Python binding
    try:
        import pytesseract
        from PIL import Image
        img = Image.open(io.BytesIO(content))
        # Preprocess to grayscale for improved OCR clarity
        if img.mode != "L":
            img = img.convert("L")
        text = pytesseract.image_to_string(img, lang="eng")
        if text and len(text.strip()) >= 15:
            return text.strip()
    except Exception:
        pass

    # Attempt 2: Direct tesseract CLI execution
    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        candidates = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            shutil.os.environ.get("TESSERACT_CMD")
        ]
        for c in candidates:
            if c and shutil.os.path.exists(c):
                tesseract_cmd = c
                break

    if not tesseract_cmd:
        return None

    try:
        proc = subprocess.run(
            [tesseract_cmd, "stdin", "stdout", "--oem", "1", "-l", "eng"],
            input=content,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=True
        )
        text = proc.stdout.decode("utf-8", errors="replace").strip()
        return text if len(text) >= 15 else None
    except Exception:
        return None


def extract_report_document(filename: str, content: bytes) -> Dict[str, Any]:
    """
    Main extraction pipeline:
    1. Identifies document type and validates presence of content.
    2. Performs genuine digital text extraction (PDF / TXT) or OCR (Images).
    3. Calculates an empirical confidence score from recognized characters and word structures.
    4. Segments only genuine clinical sections and extracts anchored findings.
    5. Never fabricates clinical findings if document is unreadable or empty.
    """
    filename_lower = filename.lower()
    raw_text = ""
    extraction_method = "Unknown"
    extraction_errors: List[Dict[str, Any]] = []
    pages_data: List[Dict[str, Any]] = []

    # Check for empty content
    if not content or len(content.strip()) == 0:
        return {
            "filename": filename,
            "extraction_method": "Empty Document Check",
            "confidence": 0.0,
            "raw_text": "",
            "pages_count": 0,
            "extraction_errors": [{
                "page": 1,
                "issue": "Uploaded document is empty (0 bytes). No text or scan data to analyze.",
                "severity": "error"
            }],
            "sections": {},
            "findings": [],
            "processing_status": "failed",
            "is_verified": False,
            "disclaimer": "Verified indicates text review by user; not clinical validation."
        }

    # 1. Digital PDF Extraction
    if filename_lower.endswith(".pdf"):
        extraction_method = "Digital PDF Parser (pypdf)"
        try:
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(content))
            page_count = len(pdf_reader.pages)
            total_chars = 0

            for i, page in enumerate(pdf_reader.pages):
                page_num = i + 1
                try:
                    page_text = page.extract_text() or ""
                except Exception:
                    page_text = ""
                clean_text = page_text.strip()
                char_count = len(clean_text)
                total_chars += char_count

                pages_data.append({
                    "page": page_num,
                    "text": clean_text,
                    "char_count": char_count
                })

            if total_chars >= 25:
                # Genuine digital PDF with text layer
                page_blocks = []
                for p in pages_data:
                    if p["text"]:
                        page_blocks.append(f"--- [PAGE {p['page']}] ---\n{p['text']}")
                raw_text = "\n\n".join(page_blocks)
            else:
                # Scanned image-based PDF without embedded text layer.
                # Attempt OCR on embedded scanned page images across all pages.
                extraction_method = "Scanned PDF (OCR Scan Extraction)"
                scanned_ocr_blocks = []
                scanned_ocr_success = False

                for i, page in enumerate(pdf_reader.pages):
                    page_num = i + 1
                    page_ocr_parts = []
                    # Extract images embedded on page
                    if hasattr(page, "images") and page.images:
                        for img_obj in page.images:
                            try:
                                img_bytes = img_obj.data
                                ocr_result = try_ocr_image(img_bytes)
                                if ocr_result and len(ocr_result.strip()) >= 15:
                                    page_ocr_parts.append(ocr_result.strip())
                            except Exception:
                                pass
                    if page_ocr_parts:
                        page_combined = "\n".join(page_ocr_parts)
                        scanned_ocr_blocks.append(f"--- [PAGE {page_num}] ---\n{page_combined}")
                        for p in pages_data:
                            if p["page"] == page_num:
                                p["text"] = page_combined
                                p["char_count"] = len(page_combined)
                        scanned_ocr_success = True

                if scanned_ocr_success and scanned_ocr_blocks:
                    raw_text = "\n\n".join(scanned_ocr_blocks)
                    extraction_method = "Scanned PDF (Optical OCR Engine)"
                else:
                    extraction_method = "Scanned PDF (OCR Engine Did Not Detect Text)"
                    extraction_errors.append({
                        "page": 1,
                        "issue": "Scanned document detected without an embedded text layer. OCR was executed on embedded scan images but found no legible clinical report text. PathoGuard will never fabricate findings.",
                        "severity": "error"
                    })
                    raw_text = ""
        except Exception as e:
            extraction_method = "PDF Parser Error"
            extraction_errors.append({
                "page": 1,
                "issue": f"PDF parsing error: {str(e)}. File may be corrupted or password-protected.",
                "severity": "error"
            })
            raw_text = ""

    # 2. Image Optical Extraction (PNG, JPG, JPEG)
    elif filename_lower.endswith((".png", ".jpg", ".jpeg")):
        extraction_method = "Optical Character Recognition (Image OCR)"
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            width, height = img.size
            mode = img.mode

            pages_data.append({
                "page": 1,
                "dimensions": f"{width}x{height}",
                "mode": mode,
                "char_count": 0
            })

            if width < 400 or height < 400:
                extraction_errors.append({
                    "page": 1,
                    "issue": f"Low resolution image detected ({width}x{height} px). Text legibility may be compromised.",
                    "severity": "caution"
                })

            # Attempt genuine OCR strictly on visual contents; never generate findings from metadata or dimensions
            ocr_text = try_ocr_image(content)
            if ocr_text and len(ocr_text.strip()) >= 15:
                raw_text = ocr_text.strip()
                pages_data[0]["char_count"] = len(raw_text)
                pages_data[0]["text"] = raw_text
            else:
                extraction_errors.append({
                    "page": 1,
                    "issue": "Optical OCR engine did not recognize readable diagnostic report text in this image. PathoGuard does not infer clinical text from image dimensions or metadata.",
                    "severity": "error"
                })
                raw_text = ""
        except Exception as e:
            extraction_method = "Image Parser Error"
            extraction_errors.append({
                "page": 1,
                "issue": f"Image format error: {str(e)}",
                "severity": "error"
            })
            raw_text = ""

    # 3. Plain Text Clinical Documents (.txt)
    elif filename_lower.endswith(".txt"):
        extraction_method = "Plain Clinical Text Parser"
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            raw_text = content.decode("latin-1", errors="replace")
            extraction_errors.append({
                "page": 1,
                "issue": "Non-UTF8 character encoding encountered; fallback Latin-1 encoding applied.",
                "severity": "notice"
            })
        pages_data.append({"page": 1, "char_count": len(raw_text), "text": raw_text})

    # 4. Compute empirical quality, segment structures, and extract anchored findings
    has_text = bool(raw_text and len(raw_text.strip()) >= 15)

    if has_text:
        confidence = calculate_extraction_quality(raw_text, pages_data)
        sections = segment_report_structure(raw_text)
        findings = extract_findings_with_passage_anchors(raw_text, sections, pages_data)
        processing_status = "needs_review"
    else:
        confidence = 0.0
        sections = {}
        findings = []
        processing_status = "failed"

    return {
        "filename": filename,
        "extraction_method": extraction_method,
        "confidence": confidence,
        "raw_text": raw_text,
        "pages_count": len(pages_data) if pages_data else 1,
        "extraction_errors": extraction_errors,
        "sections": sections,
        "findings": findings,
        "processing_status": processing_status,
        "is_verified": False,
        "disclaimer": "Verified indicates text review by user; not clinical validation."
    }


def segment_report_structure(text: str) -> Dict[str, str]:
    """
    Identifies and segments text into clinical sections:
    - metadata: De-identified patient / exam info
    - technique: Acquisition modality & protocol
    - findings: Anatomical findings & observations
    - impression: Clinical summary & impression
    - recommendations: Suggested next steps
    - unclassified: Any text not belonging to standard headings

    CRITICAL RULE:
    Never inserts synthetic placeholder text. Only returns sections
    that actually match extracted text patterns.
    """
    sections: Dict[str, str] = {}
    if not text or not text.strip():
        return sections

    # Metadata extraction (accession, indication, study date)
    meta_match = re.search(
        r"(?:METADATA|CLINICAL HISTORY|INDICATION):?\s*(.*?)(?=(?:TECHNIQUE|EXAMINATION|PROTOCOL|FINDINGS|IMPRESSION|$))",
        text, re.IGNORECASE | re.DOTALL
    )
    if meta_match and meta_match.group(1).strip():
        sections["metadata"] = meta_match.group(1).strip()

    # Technique / Examination
    tech_match = re.search(
        r"(?:TECHNIQUE|EXAMINATION|PROTOCOL):?\s*(.*?)(?=(?:FINDINGS|OBSERVATIONS|IMPRESSION|CONCLUSION|$))",
        text, re.IGNORECASE | re.DOTALL
    )
    if tech_match and tech_match.group(1).strip():
        sections["technique"] = tech_match.group(1).strip()

    # Findings
    findings_match = re.search(
        r"(?:FINDINGS|OBSERVATIONS):?\s*(.*?)(?=(?:IMPRESSION|CONCLUSION|RECOMMENDATION|RECOMMENDATIONS|$))",
        text, re.IGNORECASE | re.DOTALL
    )
    if findings_match and findings_match.group(1).strip():
        sections["findings"] = findings_match.group(1).strip()

    # Impression / Conclusion
    imp_match = re.search(
        r"(?:IMPRESSION|CONCLUSION|SUMMARY):?\s*(.*?)(?=(?:RECOMMENDATION|RECOMMENDATIONS|$))",
        text, re.IGNORECASE | re.DOTALL
    )
    if imp_match and imp_match.group(1).strip():
        sections["impression"] = imp_match.group(1).strip()

    # Recommendations
    rec_match = re.search(
        r"(?:RECOMMENDATIONS?|FOLLOW-UP):?\s*(.*?)$",
        text, re.IGNORECASE | re.DOTALL
    )
    if rec_match and rec_match.group(1).strip():
        sections["recommendations"] = rec_match.group(1).strip()

    # Unclassified text (if no headings matched or substantial unparsed text remains)
    if not sections and text.strip():
        sections["unclassified"] = text.strip()[:1000]

    return sections


def extract_findings_with_passage_anchors(
    raw_text: str,
    sections: Dict[str, str],
    pages_data: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Extracts individual clinical findings strictly from actual parsed text.
    Attaches verified page numbers and passage anchors.
    Never invents findings not present in the source.
    """
    findings: List[Dict[str, Any]] = []
    if not raw_text or not raw_text.strip():
        return findings

    def find_page_for_text(snippet: str) -> int:
        if not snippet or len(pages_data) <= 1:
            return 1
        probe = snippet[:40].lower()
        for p in pages_data:
            if probe in p.get("text", "").lower():
                return p.get("page", 1)
        return 1

    uncertainty_keywords = [
        "indeterminate", "cannot exclude", "cannot rule out", "subcentimeter",
        "unclear", "equivocal", "recommend correlation", "prior imaging unavailable",
        "uncertain", "poorly visualized", "obscured"
    ]

    anchor_idx = 0

    # 1. Technique & Protocol Anchor (if present in document)
    if "technique" in sections and sections["technique"].strip():
        tech_text = sections["technique"].strip()
        page_num = find_page_for_text(tech_text)
        findings.append({
            "id": f"p{anchor_idx}",
            "section": "technique",
            "title": "Imaging Modality & Acquisition Protocol",
            "category": "significant",
            "typeLabel": "Examination Protocol",
            "body": tech_text[:300] + ("..." if len(tech_text) > 300 else ""),
            "uncertainty": False,
            "needsVerification": True,
            "verified": False,
            "page": page_num,
            "sourceRef": f"Technique · Page {page_num} · § 1"
        })
        anchor_idx += 1

    # 2. Main Anatomical Findings (if present in document)
    if "findings" in sections and sections["findings"].strip():
        f_text = sections["findings"].strip()
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', f_text) if len(s.strip()) > 15]

        if sentences:
            # Primary finding
            primary_snippet = sentences[0]
            p_num = find_page_for_text(primary_snippet)
            is_unc = any(k in primary_snippet.lower() for k in uncertainty_keywords)
            findings.append({
                "id": f"p{anchor_idx}",
                "section": "findings",
                "title": "Primary Anatomical Observation",
                "category": "uncertainty" if is_unc else "significant",
                "typeLabel": "Anatomical Finding",
                "body": primary_snippet[:300] + ("..." if len(primary_snippet) > 300 else ""),
                "uncertainty": is_unc,
                "needsVerification": True,
                "verified": False,
                "page": p_num,
                "sourceRef": f"Findings · Page {p_num} · § 1"
            })
            anchor_idx += 1

            # Secondary finding (if multiple findings exist)
            if len(sentences) > 1:
                secondary_snippet = sentences[1]
                p_num2 = find_page_for_text(secondary_snippet)
                is_unc2 = any(k in secondary_snippet.lower() for k in uncertainty_keywords)
                findings.append({
                    "id": f"p{anchor_idx}",
                    "section": "findings",
                    "title": "Secondary Anatomical Finding",
                    "category": "uncertainty" if is_unc2 else "significant",
                    "typeLabel": "Anatomical Finding",
                    "body": secondary_snippet[:300] + ("..." if len(secondary_snippet) > 300 else ""),
                    "uncertainty": is_unc2,
                    "needsVerification": True,
                    "verified": False,
                    "page": p_num2,
                    "sourceRef": f"Findings · Page {p_num2} · § 2"
                })
                anchor_idx += 1
        else:
            p_num = find_page_for_text(f_text)
            is_unc = any(k in f_text.lower() for k in uncertainty_keywords)
            findings.append({
                "id": f"p{anchor_idx}",
                "section": "findings",
                "title": "Anatomical Observation",
                "category": "uncertainty" if is_unc else "significant",
                "typeLabel": "Anatomical Finding",
                "body": f_text[:300] + ("..." if len(f_text) > 300 else ""),
                "uncertainty": is_unc,
                "needsVerification": True,
                "verified": False,
                "page": p_num,
                "sourceRef": f"Findings · Page {p_num} · § 1"
            })
            anchor_idx += 1

    # 3. Impression Anchor (if present in document)
    if "impression" in sections and sections["impression"].strip():
        imp_text = sections["impression"].strip()
        p_num = find_page_for_text(imp_text)
        is_unc = any(k in imp_text.lower() for k in uncertainty_keywords)
        findings.append({
            "id": f"p{anchor_idx}",
            "section": "impression",
            "title": "Radiological Diagnostic Impression",
            "category": "uncertainty" if is_unc else "significant",
            "typeLabel": "Radiologist Impression",
            "body": imp_text[:300] + ("..." if len(imp_text) > 300 else ""),
            "uncertainty": is_unc,
            "needsVerification": True,
            "verified": False,
            "page": p_num,
            "sourceRef": f"Impression · Page {p_num} · § 1"
        })
        anchor_idx += 1

    # 4. Recommendations Anchor (if present in document)
    if "recommendations" in sections and sections["recommendations"].strip():
        rec_text = sections["recommendations"].strip()
        p_num = find_page_for_text(rec_text)
        findings.append({
            "id": f"p{anchor_idx}",
            "section": "recommendations",
            "title": "Clinical Recommendation & Next Steps",
            "category": "significant",
            "typeLabel": "Clinical Follow-Up",
            "body": rec_text[:300] + ("..." if len(rec_text) > 300 else ""),
            "uncertainty": False,
            "needsVerification": True,
            "verified": False,
            "page": p_num,
            "sourceRef": f"Recommendations · Page {p_num} · § 1"
        })
        anchor_idx += 1

    # 5. Unclassified Text Anchor (if present in document)
    if "unclassified" in sections and sections["unclassified"].strip():
        unc_text = sections["unclassified"].strip()
        p_num = find_page_for_text(unc_text)
        findings.append({
            "id": f"p{anchor_idx}",
            "section": "unclassified",
            "title": "Unclassified Report Excerpt",
            "category": "uncertainty",
            "typeLabel": "Unclassified Passage",
            "body": unc_text[:240] + ("..." if len(unc_text) > 240 else ""),
            "uncertainty": True,
            "needsVerification": True,
            "verified": False,
            "page": p_num,
            "sourceRef": f"General · Page {p_num} · § 1"
        })
        anchor_idx += 1

    return findings


# Backward compatibility alias
extract_text_from_file = extract_report_document
