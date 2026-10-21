"""
Automated Test Suite for PathoGuard-AI API Endpoints
Runs against the live running server at http://127.0.0.1:8000
"""

import urllib.request
import urllib.error
import json
import io
import mimetypes
import uuid

import sys

# Ensure UTF-8 output if possible
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

def test_get(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "PathoGuard-Tester"})
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        data = json.loads(resp.read().decode())
        return data

def test_post_json(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "PathoGuard-Tester"}
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        return json.loads(resp.read().decode())

def test_multipart_upload(endpoint, filename, content_bytes, content_type="text/plain"):
    url = f"{BASE_URL}{endpoint}"
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    
    body = io.BytesIO()
    body.write(f"--{boundary}\r\n".encode())
    body.write(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    body.write(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.write(content_bytes)
    body.write(f"\r\n--{boundary}--\r\n".encode())
    
    data = body.getvalue()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "PathoGuard-Tester"
        }
    )
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200, f"Expected 200, got {resp.status}"
        return json.loads(resp.read().decode())

def run_all_tests():
    print("\n================ PATHOGUARD-AI API TEST SUITE ================")
    
    # 1. Root
    try:
        data = test_get("/")
        log_test("GET / (Root operational info)", data.get("status") == "Operational", f"Platform: {data.get('platform')}")
    except Exception as e:
        log_test("GET / (Root operational info)", False, str(e))

    # 2. Top-level Health Checks
    try:
        data = test_get("/health")
        log_test("GET /health (Top-level)", data.get("status") == "healthy")
    except Exception as e:
        log_test("GET /health (Top-level)", False, str(e))

    try:
        data = test_get("/api/health")
        log_test("GET /api/health (Legacy check)", data.get("status") == "healthy")
    except Exception as e:
        log_test("GET /api/health (Legacy check)", False, str(e))

    # 3. Versioned v1 Health
    try:
        data = test_get("/api/v1/health")
        log_test("GET /api/v1/health (Versioned health check)", data.get("status") == "healthy" and "version" in data)
    except Exception as e:
        log_test("GET /api/v1/health (Versioned health check)", False, str(e))

    # 4. Versioned v1 Dashboard
    try:
        data = test_get("/api/v1/dashboard")
        has_metrics = "metrics" in data and "recent_assessments" in data
        log_test("GET /api/v1/dashboard (Dashboard metrics & summaries)", has_metrics, f"Total assessments: {data['metrics']['total_assessments']}")
    except Exception as e:
        log_test("GET /api/v1/dashboard (Dashboard metrics & summaries)", False, str(e))

    # 5. Report Upload & Parsing
    sample_report_text = (
        "EXAMINATION: CHEST RADIOGRAPH (2-VIEWS PA AND LATERAL)\n\n"
        "CLINICAL HISTORY: 52-year-old female with persistent dry cough for 5 weeks.\n\n"
        "TECHNIQUE: Upright posteroanterior and lateral projections of the chest.\n\n"
        "FINDINGS:\n"
        "The lungs are well expanded without focal consolidation, pneumothorax, or large pleural effusion. "
        "Mild linear basilar atelectasis noted in left lower lobe. Cardiomediastinal silhouette is within normal limits. "
        "No acute osseous abnormality identified.\n\n"
        "IMPRESSION:\n"
        "1. No acute cardiopulmonary process or discrete parenchymal mass.\n"
        "2. Minor basilar atelectasis; correlate clinically with reported respiratory symptoms.\n\n"
        "RECOMMENDATIONS:\n"
        "Clinical follow-up with referring clinician as clinically indicated."
    )
    
    uploaded_report_id = None
    try:
        data = test_multipart_upload(
            "/api/v1/reports",
            "sample_chest_cxr.txt",
            sample_report_text.encode("utf-8"),
            "text/plain"
        )
        uploaded_report_id = data.get("report_id")
        has_findings = len(data.get("findings", [])) >= 3
        has_sections = "findings" in data.get("sections", {})
        log_test(
            "POST /api/v1/reports (Report upload and section segmentation)",
            data.get("status") == "success" and has_findings and has_sections,
            f"Report ID: {uploaded_report_id}, Findings count: {len(data.get('findings', []))}"
        )
    except Exception as e:
        log_test("POST /api/v1/reports (Report upload and section segmentation)", False, str(e))

    # 6. Report Verification
    if uploaded_report_id:
        try:
            verify_payload = {
                "report_id": uploaded_report_id,
                "verified_findings": [
                    {
                        "id": "p1",
                        "finding": "Verified: Minor basilar atelectasis without mass.",
                        "section": "findings",
                        "verified": True
                    }
                ],
                "notes": "Verified by patient review."
            }
            v_data = test_post_json("/api/v1/reports/verify", verify_payload)
            log_test("POST /api/v1/reports/verify (Report verification step)", v_data.get("is_verified") is True)
        except Exception as e:
            log_test("POST /api/v1/reports/verify (Report verification step)", False, str(e))

    # 7. Create Symptom Assessment with linked report
    try:
        assessment_payload = {
            "primary_symptoms": ["Persistent dry cough", "Mild exertional shortness of breath"],
            "onset": "4-6 weeks",
            "trajectory": "Worsening",
            "frequency": "Daily",
            "age_bracket": "45-54",
            "medical_history": ["Mild asthma"],
            "patient_note": "Cough worse at night.",
            "associated_report_id": uploaded_report_id
        }
        asm_data = test_post_json("/api/v1/assessments", assessment_payload)
        is_neutral = asm_data.get("status") == "Assessment summary ready"
        has_steps = len(asm_data.get("suggested_next_steps", [])) > 0
        log_test(
            "POST /api/v1/assessments (Symptom intake & clinical reconciliation)",
            is_neutral and has_steps,
            f"Assessment ID: {asm_data.get('assessment_id')}, Status: '{asm_data.get('status')}'"
        )
    except Exception as e:
        log_test("POST /api/v1/assessments (Symptom intake & clinical reconciliation)", False, str(e))

    # 8. Get Assessment History
    try:
        hist_data = test_get("/api/v1/assessments")
        log_test(
            "GET /api/v1/assessments (Assessment history list)",
            hist_data.get("total_count", 0) >= 1,
            f"Total records retrieved: {hist_data.get('total_count')}"
        )
    except Exception as e:
        log_test("GET /api/v1/assessments (Assessment history list)", False, str(e))

    # 9. Verify Error Handling: Unsupported file type
    try:
        url = f"{BASE_URL}/api/v1/reports"
        try:
            test_multipart_upload("/api/v1/reports", "script.exe", b"malicious binary", "application/octet-stream")
            log_test("POST /api/v1/reports (Reject unsupported format)", False, "Failed to reject .exe")
        except urllib.error.HTTPError as he:
            log_test("POST /api/v1/reports (Reject unsupported format)", he.code == 400, f"Correctly returned HTTP {he.code}")
    except Exception as e:
        log_test("POST /api/v1/reports (Reject unsupported format)", False, str(e))

    print("==============================================================\n")

if __name__ == "__main__":
    run_all_tests()
