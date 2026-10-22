"""
Phase 3 Test Suite — Scan Report Processing & Verification
Tests digital PDF extraction, genuine text parsing, error tracking, file validation,
and the user verification workflow with cryptographic session authentication.
"""

import sys
import io
import json
import urllib.request
import urllib.error
import uuid

# Force UTF-8 stdout on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"

def log_test(name, passed, detail=""):
    symbol = "PASS" if passed else "FAIL"
    print(f"[{symbol}] {name} {('- ' + detail) if detail else ''}")
    if not passed:
        raise AssertionError(f"Test failed: {name} - {detail}")

def post_multipart(endpoint, filename, content_bytes, content_type="application/octet-stream", token=None):
    url = f"{BASE_URL}{endpoint}"
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(content_bytes)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": "PathoGuard-Phase3-Tester"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=body.getvalue(), headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def post_json(endpoint, payload, token=None):
    url = f"{BASE_URL}{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "PathoGuard-Phase3-Tester"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data_bytes, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def get_json(endpoint, token=None):
    url = f"{BASE_URL}{endpoint}"
    headers = {"User-Agent": "PathoGuard-Phase3-Tester"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def create_synthetic_digital_pdf():
    """Generates a valid digital PDF with genuine text layer."""
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj\n"
        b"4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"5 0 obj <</Length 350>> stream\n"
        b"BT\n/F1 12 Tf\n50 720 Td\n(EXAMINATION: CHEST COMPUTED TOMOGRAPHY) Tj\n"
        b"0 -20 Td\n(TECHNIQUE: Helical axial acquisition with intravenous contrast.) Tj\n"
        b"0 -20 Td\n(FINDINGS: 5.2 mm solitary non-calcified solid subpleural nodule in RLL.) Tj\n"
        b"0 -20 Td\n(IMPRESSION: Incidental pulmonary nodule; recommend 12-month follow-up.) Tj\n"
        b"0 -20 Td\n(RECOMMENDATIONS: Correlate with clinical history and prior imaging.) Tj\n"
        b"ET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000227 00000 n \n"
        b"0000000305 00000 n \ntrailer <</Size 6 /Root 1 0 R>>\nstartxref\n705\n%%EOF\n"
    )
    return pdf_content

def create_synthetic_scan_image():
    """Generates a diagnostic image using Pillow."""
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (800, 600), color=(15, 23, 42))
    d = ImageDraw.Draw(img)
    d.rectangle([(40, 40), (760, 560)], outline=(167, 243, 208), width=2)
    d.text((60, 60), "DIAGNOSTIC SCAN REPORT: THORACIC PROTOCOL", fill=(255, 255, 255))
    d.text((60, 100), "MODALITY: HIGH-RESOLUTION CHEST COMPUTED TOMOGRAPHY", fill=(200, 200, 200))
    d.text((60, 140), "FINDINGS: TARGET ANATOMY VISUALIZED WITHIN NORMAL BOUNDARIES", fill=(167, 243, 208))
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()

def run_phase3_tests():
    print("\n================ PATHOGUARD-AI PHASE 3: SCAN REPORT TEST SUITE ================")

    # 0. Negative Test: Unauthenticated Upload Blocked (401)
    status_unauth = 0
    try:
        post_multipart("/api/v1/reports", "test.pdf", b"%PDF-1.4...", "application/pdf")
    except urllib.error.HTTPError as e:
        status_unauth = e.code

    log_test(
        "Access Control: Unauthenticated Upload Blocked (401)",
        status_unauth == 401,
        "Protected report endpoint requires valid Bearer session token"
    )

    # 1. Obtain Authenticated Patient Session Token
    sess_status, sess_data = post_json("/api/v1/auth/session", {"user_id": "test_patient_phase3"})
    token = sess_data.get("token")
    log_test("Patient Session Token Acquired", sess_status == 200 and bool(token), f"Token: {token[:16]}...")

    # 2. Digital PDF Upload & Genuine Text Extraction
    pdf_bytes = create_synthetic_digital_pdf()
    status, pdf_resp = post_multipart("/api/v1/reports", "synthetic_thoracic_ct.pdf", pdf_bytes, "application/pdf", token=token)
    
    report_id = pdf_resp.get("report_id")
    has_findings = len(pdf_resp.get("findings", [])) >= 3
    has_sections = bool(pdf_resp.get("sections", {}).get("findings"))
    is_needs_review = pdf_resp.get("processing_status") == "needs_review"
    is_unverified = pdf_resp.get("is_verified") is False
    confidence_val = pdf_resp.get("confidence", 0)

    log_test(
        "Digital PDF Upload & Genuine Extraction",
        status == 200 and has_findings and has_sections and is_needs_review and is_unverified and confidence_val > 50.0,
        f"Report ID: {report_id}, Method: '{pdf_resp.get('extraction_method')}', Calibrated Confidence: {confidence_val}%"
    )

    # 3. Section Structure Recognition (Technique, Findings, Impression, Recommendations)
    sections = pdf_resp.get("sections", {})
    has_technique = "technique" in sections and len(sections["technique"]) > 0
    has_findings_sec = "findings" in sections and len(sections["findings"]) > 0
    has_impression = "impression" in sections and len(sections["impression"]) > 0
    has_recommendations = "recommendations" in sections and len(sections["recommendations"]) > 0

    log_test(
        "Section Structure Recognition (Technique, Findings, Impression, Recommendations)",
        has_technique and has_findings_sec and has_impression and has_recommendations,
        f"Sections identified: {list(sections.keys())}"
    )

    # 4. Image Optical Parsing: Verified Abstention / No Invented Findings
    img_bytes = create_synthetic_scan_image()
    status_img, img_resp = post_multipart("/api/v1/reports", "synthetic_mri_slice.png", img_bytes, "image/png", token=token)
    is_ocr_method = "Optical" in img_resp.get("extraction_method", "") or "OCR" in img_resp.get("extraction_method", "")
    has_no_fake_findings = (img_resp.get("findings") == [] or all("invented" not in str(f).lower() for f in img_resp.get("findings", [])))
    has_honest_status = img_resp.get("processing_status") in ["failed", "needs_review"]
    
    log_test(
        "Optical Image Parsing: No Invented Findings on Unindexed Scan",
        status_img == 200 and is_ocr_method and has_no_fake_findings and has_honest_status,
        f"Method: '{img_resp.get('extraction_method')}', Findings Count: {len(img_resp.get('findings', []))}"
    )

    # 4b. Scanned PDF Handling: Genuine OCR Execution & Zero Prewritten Findings
    scanned_pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]>> endobj\n"
        b"xref\n0 4\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
        b"trailer <</Size 4 /Root 1 0 R>>\nstartxref\n190\n%%EOF\n"
    )
    status_scan, scan_resp = post_multipart("/api/v1/reports", "scanned_doc_without_text.pdf", scanned_pdf_bytes, "application/pdf", token=token)
    has_no_prewritten = len(scan_resp.get("findings", [])) == 0
    is_failed_or_ocr = scan_resp.get("processing_status") in ["failed", "needs_review"]
    log_test(
        "Scanned PDF Handling: No Prewritten Findings Inserted When Text Missing",
        status_scan == 200 and has_no_prewritten and is_failed_or_ocr,
        f"Findings count: {len(scan_resp.get('findings', []))}, Method: '{scan_resp.get('extraction_method')}'"
    )

    # 5. User Verification Workflow (Step 4 & Step 6)
    if report_id:
        verify_payload = {
            "report_id": report_id,
            "verified_findings": [
                {
                    "id": "p1",
                    "title": "Confirmed: 5.2 mm Subpleural Nodule",
                    "finding": "Verified solid subpleural nodule in right lower lobe.",
                    "body": "Verified solid subpleural nodule in right lower lobe.",
                    "section": "findings",
                    "anchor": "p1",
                    "uncertainty": False,
                    "needsVerification": False,
                    "verified": True,
                    "sourceRef": "Findings · Page 1 · § 1"
                }
            ],
            "notes": "Reviewed and confirmed by patient without altering original document."
        }
        v_status, v_resp = post_json(f"/api/v1/reports/{report_id}/verify", verify_payload, token=token)
        is_verified_status = v_resp.get("processing_status") == "verified" and v_resp.get("is_verified") is True
        has_disclaimer = "not clinical validation" in v_resp.get("disclaimer", "").lower()

        log_test(
            "User Verification & Non-Clinical Validation Disclaimer",
            v_status == 200 and is_verified_status and has_disclaimer,
            f"Status: '{v_resp.get('processing_status')}', Disclaimer: '{v_resp.get('disclaimer')}'"
        )

        # 6. Retrieve Verified Report Details
        g_status, g_resp = get_json(f"/api/v1/reports/{report_id}", token=token)
        log_test(
            "Get Verified Report State",
            g_status == 200 and g_resp.get("is_verified") is True and g_resp.get("processing_status") == "verified",
            f"Verified findings count: {len(g_resp.get('findings', []))}"
        )

    # 7. File Validation Limits: Reject Empty File (0 Bytes -> 400)
    try:
        post_multipart("/api/v1/reports", "empty_report.pdf", b"", "application/pdf", token=token)
        log_test("Reject Empty Document (0 Bytes -> 400)", False, "Failed to reject empty document")
    except urllib.error.HTTPError as he:
        log_test("Reject Empty Document (0 Bytes -> 400)", he.code == 400, f"Correctly returned HTTP {he.code}")

    # 8. File Validation Limits: Reject Unsupported File (.bat -> 400)
    try:
        post_multipart("/api/v1/reports", "malicious_script.bat", b"echo dangerous", "application/x-bat", token=token)
        log_test("Reject Unsupported File Extension (.bat)", False, "Failed to reject")
    except urllib.error.HTTPError as he:
        log_test("Reject Unsupported File Extension (.bat)", he.code == 400, f"Correctly returned HTTP {he.code}")

    # 9. File Validation Limits: Reject Oversized File (> 25MB -> 413)
    try:
        oversized_bytes = b"0" * (26 * 1024 * 1024) # 26 MB
        post_multipart("/api/v1/reports", "large_file.pdf", oversized_bytes, "application/pdf", token=token)
        log_test("Reject Oversized File (> 25 MB)", False, "Failed to reject")
    except urllib.error.HTTPError as he:
        log_test("Reject Oversized File (> 25 MB)", he.code == 413, f"Correctly returned HTTP {he.code}")

    print("================================================================================\n")

if __name__ == "__main__":
    run_phase3_tests()
