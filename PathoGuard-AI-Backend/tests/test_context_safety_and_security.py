"""
Context-Aware Clinical Safety & Cryptographic Security Verification Suite
Validates:
1. Contextual negation handling (denies hemoptysis, no lower GI bleeding -> no false emergency alerts)
2. Historical vs acute symptom differentiation (remote history -> no acute alert)
3. Acute emergency recognition (frank blood, severe dyspnea -> acute alert triggered)
4. Cryptographic HMAC session token issuance & verification
5. Server-side cross-user record isolation & unauthorized deletion prevention
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.clinical_safety import evaluate_clinical_safety
from app.core.auth import (
    generate_session_token,
    verify_session_token,
    AuthenticatedUser,
    assert_record_ownership
)
from app.db.repository import (
    save_assessment_record,
    get_assessment_record,
    delete_assessment_record
)
from fastapi import HTTPException


def run_tests():
    print("================ CLINICAL SAFETY & SECURITY TEST SUITE ================")
    passed = 0
    total = 0

    def test(name, condition, extra=""):
        nonlocal passed, total
        total += 1
        if condition:
            passed += 1
            print(f"[PASS] {name} {extra}".strip())
        else:
            print(f"[FAIL] {name} {extra}".strip())
            raise AssertionError(f"Test failed: {name}")

    # --------------------------------------------------------------------------
    # 1. Negation Handling in Clinical Safety Pathway
    # --------------------------------------------------------------------------
    res_neg_1 = evaluate_clinical_safety(
        symptoms=["Persistent cough for 3 weeks"],
        patient_note="Patient explicitly denies hemoptysis or coughing up blood."
    )
    test("Negation Handling: 'denies hemoptysis' does not trigger red flag",
         not res_neg_1.is_urgent and "Hemoptysis (Coughing blood)" in res_neg_1.negated_findings,
         f"- Negated: {res_neg_1.negated_findings}")

    res_neg_2 = evaluate_clinical_safety(
        symptoms=["Mild abdominal discomfort"],
        patient_note="No blood in stool, denies rectal bleeding, no unintentional weight loss."
    )
    test("Negation Handling: Multiple denied symptoms correctly suppressed",
         not res_neg_2.is_urgent and len(res_neg_2.negated_findings) >= 2,
         f"- Total negated: {len(res_neg_2.negated_findings)}")

    res_neg_3 = evaluate_clinical_safety(
        symptoms=["Fatigue"],
        patient_note="Patient has no dysphagia and is not experiencing difficulty swallowing."
    )
    test("Negation Handling: 'no dysphagia' suppressed",
         not res_neg_3.is_urgent and len(res_neg_3.negated_findings) >= 1)

    # --------------------------------------------------------------------------
    # 2. Historical & Remote Condition Differentiation
    # --------------------------------------------------------------------------
    res_hist_1 = evaluate_clinical_safety(
        symptoms=["Routine health check"],
        patient_note="History of jaundice 10 years ago, completely resolved."
    )
    test("Temporality Handling: Remote resolved jaundice does not trigger acute emergency",
         not res_hist_1.is_urgent and len(res_hist_1.historical_findings) >= 1,
         f"- Historical findings: {res_hist_1.historical_findings}")

    # --------------------------------------------------------------------------
    # 3. Acute Active Red Flag Recognition
    # --------------------------------------------------------------------------
    res_acute_1 = evaluate_clinical_safety(
        symptoms=["Persistent cough"],
        patient_note="Started coughing up frank blood and dark clots since yesterday."
    )
    test("Acute Recognition: Active frank blood triggers emergency review",
         res_acute_1.is_urgent and "Hemoptysis (Coughing blood)" in res_acute_1.active_red_flags,
         f"- Category: {res_acute_1.triage_category}")

    res_acute_2 = evaluate_clinical_safety(
        symptoms=["Severe shortness of breath", "Inability to breathe when recumbent"],
        patient_note="Stridor and audible wheeze present."
    )
    test("Acute Recognition: Severe airway distress triggers emergency review",
         res_acute_2.is_urgent and ("Acute / Severe Respiratory Distress" in res_acute_2.active_red_flags),
         f"- Active flags: {res_acute_2.active_red_flags}")

    res_mixed = evaluate_clinical_safety(
        symptoms=["Coughing blood"],
        patient_note="Patient denies fever or chills, but has active coughing blood."
    )
    test("Mixed Presentation: Denying fever does not suppress genuine hemoptysis",
         res_mixed.is_urgent and len(res_mixed.active_red_flags) >= 1)

    # --------------------------------------------------------------------------
    # 4. Cryptographic HMAC-SHA256 Session Token Security
    # --------------------------------------------------------------------------
    token_user_a = generate_session_token("patient_alpha_123")
    test("HMAC Session Issuance: Generates valid token string",
         token_user_a.startswith("pgs_") and "." in token_user_a)

    verified_a = verify_session_token(token_user_a)
    test("HMAC Session Verification: Valid signature decodes exact UID",
         verified_a is not None and verified_a["uid"] == "patient_alpha_123")

    # Test tampering
    tampered_token = token_user_a[:-4] + "ffff"
    verified_tampered = verify_session_token(tampered_token)
    test("HMAC Tampering Defense: Tampered token signature rejected",
         verified_tampered is None)

    # Test expired token
    expired_token = generate_session_token("patient_exp", validity_seconds=-10)
    verified_expired = verify_session_token(expired_token)
    test("HMAC Expiry Defense: Expired token rejected",
         verified_expired is None)

    # --------------------------------------------------------------------------
    # 5. Server-Side Cross-User Record Isolation & Ownership Authorization
    # --------------------------------------------------------------------------
    user_alpha = AuthenticatedUser(user_id="patient_alpha_123", is_authenticated=True)
    user_beta = AuthenticatedUser(user_id="patient_beta_456", is_authenticated=True)

    # Create record owned by user_alpha
    test_asm_id = "ASM-TEST-AUTH-001"
    save_assessment_record({
        "id": test_asm_id,
        "created_at": "2026-10-21T22:00:00",
        "assessment_type": "Security Test",
        "status": "Ready",
        "summary": "Confidential patient record",
        "patient_reported": {"primary_symptoms": ["cough"]},
        "report_findings": [],
        "missing_or_conflicting": [],
        "suggested_next_steps": []
    }, user_id="patient_alpha_123")

    # User Alpha retrieves their own record -> Success
    rec_alpha = get_assessment_record(test_asm_id, user_id=user_alpha.user_id)
    test("Record Isolation: User Alpha can access their own record",
         rec_alpha is not None and rec_alpha["id"] == test_asm_id)

    # User Beta attempts to retrieve User Alpha's record -> Blocked (None)
    rec_beta = get_assessment_record(test_asm_id, user_id=user_beta.user_id)
    test("Record Isolation: User Beta is blocked from accessing User Alpha's record",
         rec_beta is None)

    # Assert ownership check failure
    ownership_blocked = False
    try:
        assert_record_ownership(record_owner_id="patient_alpha_123", user=user_beta)
    except HTTPException as e:
        if e.status_code == 403:
            ownership_blocked = True
    test("Server-Side Ownership Gate: Unauthorized cross-user operation raises HTTP 403",
         ownership_blocked)

    # User Beta attempts to delete User Alpha's record -> Blocked
    del_beta_res = delete_assessment_record(test_asm_id, user_id=user_beta.user_id)
    test("Record Isolation: User Beta cannot delete User Alpha's record",
         del_beta_res is False)

    # User Alpha deletes their own record -> Success
    del_alpha_res = delete_assessment_record(test_asm_id, user_id=user_alpha.user_id)
    test("Record Deletion: User Alpha successfully deletes their own record",
         del_alpha_res is True)

    print(f"\n================ ALL SAFETY & SECURITY TESTS PASSED ({passed}/{total}) ================\n")


if __name__ == "__main__":
    run_tests()
