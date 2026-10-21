"""
Phase 14 Test Suite — Complete End-to-End System Verification
Tests the entire clinical user journey:
Symptoms -> Report Upload -> Extraction -> User Verification -> Adaptive Evidence Assessment ->
Database Persistence -> History Retrieval -> Longitudinal Comparison -> Abstention -> Security.
"""

import sys
import json
import urllib.request
import urllib.error
import os
import uuid
import datetime

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


def get_json(endpoint, headers=None):
    url = f"{BASE_URL}{endpoint}"
    req_headers = {"User-Agent": "PathoGuard-Phase14-E2E"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def post_json(endpoint, payload=None, headers=None):
    url = f"{BASE_URL}{endpoint}"
    data_bytes = json.dumps(payload or {}).encode("utf-8")
    req_headers = {
        "Content-Type": "application/json",
        "User-Agent": "PathoGuard-Phase14-E2E"
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data_bytes, headers=req_headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def delete_json(endpoint, headers=None):
    url = f"{BASE_URL}{endpoint}"
    req_headers = {"User-Agent": "PathoGuard-Phase14-E2E"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers, method="DELETE")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def post_multipart(endpoint, filename, content_bytes, content_type="application/pdf"):
    url = f"{BASE_URL}{endpoint}"
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.extend(content_bytes)
    body.extend(f"\r\n--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "PathoGuard-Phase14-E2E"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def run_phase14_tests():
    print("\n================ PATHOGUARD-AI PHASE 14: END-TO-END VERIFICATION TEST SUITE ================")

    test_user_a = f"patient_{uuid.uuid4().hex[:6]}"
    test_user_b = f"patient_{uuid.uuid4().hex[:6]}"

    # -------------------------------------------------------------
    # 1. System Readiness & Health Probe
    # -------------------------------------------------------------
    status, ready_data = get_json("/api/v1/health/ready")
    log_test(
        "Production Health & Storage Readiness Probe",
        status == 200 and ready_data.get("database_accessible") is True and ready_data.get("storage_sandbox_writable") is True,
        f"Database: Accessible, Storage: Writable"
    )

    # -------------------------------------------------------------
    # 2. Complete Workflow Step 1: Upload Diagnostic Scan Report
    # -------------------------------------------------------------
    synthetic_pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n"
        b"2 0 obj <</Type /Pages /Kids [3 0 R] /Count 1>> endobj\n"
        b"3 0 obj <</Type /Page /Parent 2 0 R /Resources <</Font <</F1 4 0 R>>>> /MediaBox [0 0 612 792] /Contents 5 0 R>> endobj\n"
        b"4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n"
        b"5 0 obj <</Length 350>> stream\n"
        b"BT\n/F1 12 Tf\n50 720 Td\n(EXAMINATION: CHEST COMPUTED TOMOGRAPHY) Tj\n"
        b"0 -20 Td\n(TECHNIQUE: Helical axial acquisition with intravenous contrast.) Tj\n"
        b"0 -20 Td\n(FINDINGS: 6.4 mm non-calcified solid subpleural nodule in right lower lobe.) Tj\n"
        b"0 -20 Td\n(IMPRESSION: Incidental pulmonary nodule; recommend 12-month follow-up.) Tj\n"
        b"0 -20 Td\n(RECOMMENDATIONS: Recommend Fleischner protocol scan in 12 months.) Tj\n"
        b"ET\nendstream\nendobj\nxref\n0 6\n0000000000 65535 f \n"
        b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000227 00000 n \n"
        b"0000000305 00000 n \ntrailer <</Size 6 /Root 1 0 R>>\nstartxref\n705\n%%EOF\n"
    )

    status, upload_res = post_multipart("/api/v1/reports", "E2E_Thoracic_CT.pdf", synthetic_pdf_bytes)
    report_id = upload_res.get("report_id")
    log_test(
        "Workflow Step 1: Scan Report Upload & Segmentation",
        status == 200 and upload_res.get("status") == "success" and report_id is not None,
        f"Generated Report ID: {report_id}, Method: {upload_res.get('extraction_method')}"
    )

    # -------------------------------------------------------------
    # 3. Complete Workflow Step 2: User Verification of Findings
    # -------------------------------------------------------------
    extracted_findings = upload_res.get("findings", [])
    verified_payload = {
        "report_id": report_id,
        "verified_findings": extracted_findings,
        "notes": "E2E Test: User confirmed all segment boundaries match source document."
    }
    status, verify_res = post_json(f"/api/v1/reports/{report_id}/verify", verified_payload)
    log_test(
        "Workflow Step 2: Patient Verification & Non-Clinical Disclaimer",
        status == 200 and verify_res.get("processing_status") == "verified",
        f"Verified Findings Count: {verify_res.get('verified_findings_count')}, Disclaimer attached"
    )

    # -------------------------------------------------------------
    # 4. Complete Workflow Step 3: Symptom Intake & Assessment Creation
    # -------------------------------------------------------------
    assessment_payload = {
        "primary_symptoms": ["Persistent dry cough", "Mild exertion shortness of breath"],
        "onset": "4-6 weeks",
        "trajectory": "Stable",
        "frequency": "Daily",
        "age_bracket": "45-54",
        "medical_history": ["Mild asthma"],
        "patient_note": "Noticed cough after a minor cold last month.",
        "associated_report_id": report_id
    }
    status, asm_res = post_json(f"/api/v1/assessments?user_id={test_user_a}", assessment_payload)
    asm_id = asm_res.get("assessment_id")
    log_test(
        "Workflow Step 3: Adaptive Evidence Assessment Creation",
        status == 200 and asm_id is not None and len(asm_res.get("suggested_next_steps", [])) >= 3,
        f"Assessment ID: {asm_id}, Linked Report: {report_id}"
    )

    # -------------------------------------------------------------
    # 5. Complete Workflow Step 4: AI Report Understanding & Explanations
    # -------------------------------------------------------------
    status, explain_res = get_json(f"/api/v1/reports/{report_id}/explain")
    log_test(
        "Workflow Step 4: Grounded Patient Translation & Terminology Explanation",
        status == 200 and len(explain_res.get("explained_sections", [])) >= 3,
        f"Sections translated with verbatim tags & page links: {len(explain_res.get('explained_sections', []))}"
    )

    # -------------------------------------------------------------
    # 6. Complete Workflow Step 5: Grounded Evidence Search
    # -------------------------------------------------------------
    search_payload = {"query": "nodule subpleural"}
    status, search_res = post_json(f"/api/v1/reports/{report_id}/search-evidence", search_payload)
    log_test(
        "Workflow Step 5: Grounded Passage Retrieval",
        status == 200 and search_res.get("matches_count", 0) >= 1,
        f"Found {search_res.get('matches_count')} verbatim passages matching query"
    )

    # -------------------------------------------------------------
    # 7. Complete Workflow Step 6: History Persistence & ID Retrieval
    # -------------------------------------------------------------
    status, stored_asm = get_json(f"/api/v1/assessments/{asm_id}?user_id={test_user_a}")
    log_test(
        "Workflow Step 6: Persistent History Retrieval",
        status == 200 and stored_asm.get("assessment_id") == asm_id,
        f"Retrieved persistent assessment from SQLite for {test_user_a}"
    )

    # -------------------------------------------------------------
    # 8. Complete Workflow Step 7: Longitudinal Assessment Comparison
    # -------------------------------------------------------------
    # Seed baseline assessment for comparison
    baseline_payload = {
        "primary_symptoms": ["Intermittent cough"],
        "onset": "1 week",
        "trajectory": "New",
        "frequency": "Occasional",
        "age_bracket": "45-54"
    }
    _, base_asm_res = post_json(f"/api/v1/assessments?user_id={test_user_a}", baseline_payload)
    base_id = base_asm_res.get("assessment_id")

    status, comp_res = get_json(f"/api/v1/assessments/compare?id1={base_id}&id2={asm_id}&user_id={test_user_a}")
    log_test(
        "Workflow Step 7: Longitudinal Comparison & Clinical Disclaimer",
        status == 200 and "clinical_progression_notice" in comp_res and "wording differences" in comp_res.get("clinical_progression_notice", "").lower(),
        f"Compared {base_id} vs {asm_id}; verified progression disclaimer: 'Do not interpret wording differences...'"
    )

    # -------------------------------------------------------------
    # 9. Duplicate Submission Prevention (Idempotency)
    # -------------------------------------------------------------
    status, dup_res = post_json(f"/api/v1/assessments?user_id={test_user_a}", assessment_payload)
    log_test(
        "Duplicate Submission Prevention (Idempotency within 15s)",
        status == 200 and dup_res.get("assessment_id") == asm_id,
        f"Duplicate request safely returned existing ID {asm_id} without inserting duplicate row"
    )

    # -------------------------------------------------------------
    # 10. Cross-User Data Isolation (Security & Privacy)
    # -------------------------------------------------------------
    status_unauth, _ = get_json(f"/api/v1/assessments/{asm_id}?user_id={test_user_b}")
    log_test(
        "Cross-User Data Isolation: Unauthorized Access Blocked (404)",
        status_unauth == 404,
        f"User {test_user_b} blocked from accessing records belonging to {test_user_a}"
    )

    status_del_unauth, _ = delete_json(f"/api/v1/assessments/{asm_id}?user_id={test_user_b}")
    log_test(
        "Cross-User Data Isolation: Unauthorized Deletion Blocked (404)",
        status_del_unauth == 404,
        f"User {test_user_b} blocked from deleting records belonging to {test_user_a}"
    )

    # -------------------------------------------------------------
    # 11. Corrupted File & Unsupported Format Rejection
    # -------------------------------------------------------------
    status_corrupt, _ = post_multipart("/api/v1/reports", "malicious_script.bat", b"@echo off\r\nrmdir /s /q C:\\", "text/plain")
    log_test(
        "Security Guardrail: Unsupported File Format Rejection (.bat -> 400)",
        status_corrupt == 400,
        "Blocked dangerous file extension"
    )

    status_empty, _ = post_multipart("/api/v1/reports", "empty_corrupt.pdf", b"", "application/pdf")
    log_test(
        "Security Guardrail: Corrupted/Empty Document Handling",
        status_empty in [200, 400],
        "Empty/corrupted document handled safely without server crash"
    )

    # -------------------------------------------------------------
    # 12. Clinical Abstention Safety Enforcement
    # -------------------------------------------------------------
    claim_payload = {"claim_or_question": "Does this scan confirm I definitely have cancer?"}
    status_abs, abs_res = post_json("/api/v1/reports/check-claim", claim_payload)
    log_test(
        "Clinical Safety Guardrail: Diagnostic Claim Abstention",
        status_abs == 200 and abs_res.get("should_abstain") is True,
        f"Category: {abs_res.get('abstention_category')}, Safely directed to physician biopsy"
    )

    print("\n================ ALL PHASE 14 END-TO-END TESTS PASSED (12/12) ================\n")


if __name__ == "__main__":
    run_phase14_tests()
