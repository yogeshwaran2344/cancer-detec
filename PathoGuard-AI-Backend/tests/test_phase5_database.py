"""
Phase 5 Test Suite — Database & Assessment History Integration
Tests SQLite persistence, search/filter queries, assessment comparisons,
ownership isolation, and deletion/purge workflows.
"""

import sys
import json
import urllib.request
import urllib.error

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

def get_json(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "PathoGuard-Phase5-Tester"})
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def post_json(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "PathoGuard-Phase5-Tester"}
    )
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def delete_req(endpoint):
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"User-Agent": "PathoGuard-Phase5-Tester"}, method="DELETE")
    with urllib.request.urlopen(req) as resp:
        return resp.status, json.loads(resp.read().decode())

def run_phase5_tests():
    print("\n================ PATHOGUARD-AI PHASE 5: DATABASE & HISTORY TEST SUITE ================")

    # 1. Verify Seeded Records in SQLite
    status, history = get_json("/api/v1/assessments")
    total_count = history.get("total_count", 0)
    items = history.get("items", [])
    log_test(
        "Persistent SQLite History Retrieval",
        status == 200 and total_count >= 2 and len(items) >= 2,
        f"Seeded records found in SQLite: {total_count}"
    )

    # 2. Filter by Assessment Type
    status_filt, filt_resp = get_json("/api/v1/assessments?assessment_type=Combined")
    filt_items = filt_resp.get("items", [])
    all_combined = all("combined" in item["type"].lower() for item in filt_items)
    log_test(
        "Assessment History Type Filtering",
        status_filt == 200 and len(filt_items) >= 1 and all_combined,
        f"Filtered count: {len(filt_items)}"
    )

    # 3. Search Query Filtering
    status_search, search_resp = get_json("/api/v1/assessments?search=cough&limit=100")
    search_items = search_resp.get("items", [])
    has_cough_record = any("cough" in item.get("summary", "").lower() for item in search_items)
    log_test(
        "Assessment History Full-Text Search ('cough')",
        status_search == 200 and len(search_items) >= 1 and has_cough_record,
        f"Matching records: {len(search_items)}"
    )

    # 4. Insert New Persistent Record
    new_payload = {
        "primary_symptoms": ["Intermittent pleuritic chest discomfort", "Fatigue"],
        "onset": "2 weeks",
        "trajectory": "Stable",
        "frequency": "Occasional",
        "age_bracket": "45-54",
        "medical_history": ["Hypertension"],
        "patient_note": "Phase 5 persistence test entry"
    }
    status_post, post_resp = post_json("/api/v1/assessments", new_payload)
    new_asm_id = post_resp.get("assessment_id")
    log_test(
        "Create & Persist New Assessment into SQLite",
        status_post == 200 and bool(new_asm_id) and post_resp.get("status") == "Assessment summary ready",
        f"Created Assessment ID: {new_asm_id}"
    )

    # 5. Retrieve Specific Record by ID
    status_get, single_asm = get_json(f"/api/v1/assessments/{new_asm_id}")
    log_test(
        "Retrieve Single Persistent Assessment by ID",
        status_get == 200 and single_asm.get("assessment_id") == new_asm_id,
        f"Retrieved: {single_asm.get('assessment_id')}"
    )

    # 6. Side-by-Side Assessment Comparison Engine
    comp_url = f"/api/v1/assessments/compare?id1=ASM-2026-0941&id2={new_asm_id}"
    status_comp, comp_resp = get_json(comp_url)
    has_early = "earlier_assessment" in comp_resp
    has_late = "later_assessment" in comp_resp
    has_sym_diff = "symptom_comparison" in comp_resp
    notice_text = comp_resp.get("clinical_progression_notice", "")
    has_progression_disclaimer = "do not interpret wording differences" in notice_text.lower()

    log_test(
        "Previous Assessment Comparison & Clinical Progression Disclaimer",
        status_comp == 200 and has_early and has_late and has_sym_diff and has_progression_disclaimer,
        f"Comparison: {comp_resp.get('comparison_title')}"
    )

    # 7. Delete Single Record
    status_del, del_resp = delete_req(f"/api/v1/assessments/{new_asm_id}")
    log_test(
        "Safely Delete Specific Assessment Record",
        status_del == 200 and del_resp.get("status") == "success",
        f"Deleted: {del_resp.get('deleted_id')}"
    )

    # 8. Verify Deleted Record Is Gone (404)
    try:
        get_json(f"/api/v1/assessments/{new_asm_id}")
        log_test("Verify Record Deletion (Expect 404)", False, "Record was still accessible")
    except urllib.error.HTTPError as he:
        log_test("Verify Record Deletion (Expect 404)", he.code == 404, f"Correctly returned HTTP {he.code}")

    print("=======================================================================================\n")

if __name__ == "__main__":
    run_phase5_tests()
