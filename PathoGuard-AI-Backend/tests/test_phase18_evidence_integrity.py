"""
PathoGuard-AI — Phase 18 Evidence Integrity & Adaptive Reconciliation Test Suite
Verifies:
1. Evidence Dependency Mapping & Subgraph Invalidation
2. Selective Recomputation & Computational Savings
3. Report Comparability Gate (RECIST & Cross-Modality Safety)
4. Minimum-Information Acquisition (Burden vs Uncertainty Optimization)
5. Privacy-Preserving PHI De-identification Layer
6. 6-Stage Integrated Pipeline Execution
7. Empirical Benchmark Execution & Metric Validation
"""

import sys
import json
import urllib.request
import urllib.error

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "http://127.0.0.1:8000"


def log_test(name: str, passed: bool, detail: str = ""):
    symbol = "PASS" if passed else "FAIL"
    print(f"[{symbol}] {name} {('- ' + detail) if detail else ''}")
    if not passed:
        raise AssertionError(f"Test failed: {name} - {detail}")


def post_json(endpoint: str, data: dict) -> dict:
    url = f"{BASE_URL}{endpoint}"
    payload = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_json(endpoint: str) -> dict:
    url = f"{BASE_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def test_feature1_dependency_graph():
    """Test Feature 1: DAG creation, parent-child edge tracking, and node retrieval."""
    sample_report = {
        "report_id": "RPT-TEST-001",
        "sections": {
            "technique": "Axial IV contrast chest CT 2.0 mm.",
            "findings": "2.4 cm solitary nodule right lower lobe. No adenopathy.",
            "impression": "Solitary pulmonary nodule. Follow-up PET-CT recommended."
        },
        "findings": [
            {"finding": "2.4 cm pulmonary nodule right lower lobe", "category": "Pulmonary"},
            {"finding": "No adenopathy", "category": "Lymphatic"}
        ]
    }

    res = post_json("/api/v1/evidence/dependency-graph", sample_report)
    nodes = res.get("nodes", {})

    log_test(
        "Feature 1.1: Evidence Dependency DAG Construction",
        res.get("total_nodes", 0) >= 5 and "src_findings" in nodes,
        f"Total graph nodes created: {res.get('total_nodes')} with root source fragments"
    )

    findings_node = nodes.get("fnd_item_1", {})
    parents = findings_node.get("parent_ids", [])
    log_test(
        "Feature 1.2: Fine-Grained Provenance Traceability",
        "src_findings" in parents,
        f"Finding node correctly linked to parent source anchor: {parents}"
    )


def test_feature1_selective_recomputation():
    """Test Feature 1: Downstream invalidation and selective recomputation."""
    payload = {
        "report_data": {
            "report_id": "RPT-TEST-002",
            "sections": {
                "technique": "Non-contrast chest CT.",
                "findings": "Suspicious 3.0 cm mass left lung apex.",
                "impression": "Probable primary apical bronchogenic carcinoma."
            },
            "findings": [
                {"finding": "3.0 cm mass left lung apex", "category": "Pulmonary"}
            ]
        },
        "node_id": "src_findings",
        "new_content": "Resolved post-infectious opacity 0.4 cm left lung apex (verified clean margin).",
        "reason": "Radiology revision following comparison with historical baseline"
    }

    res = post_json("/api/v1/evidence/change-impact", payload)
    impact = res.get("impact_result", {})
    recomputed = impact.get("recomputed_count", 0)
    savings = impact.get("savings_percentage", 0.0)

    log_test(
        "Feature 1.3: Downstream Subgraph Invalidation & Selective Recompute",
        recomputed >= 1 and savings > 0,
        f"Selectively recomputed {recomputed} affected nodes; computational savings: {savings}%"
    )

    audit = res.get("audit_log", [])
    log_test(
        "Feature 1.4: Provenance Mutation Audit Trail",
        len(audit) >= 2,
        f"Audit trail recorded {len(audit)} lifecycle events with timestamps and rationale"
    )


def test_feature2_comparability_gate():
    """Test Feature 2: Anatomical and modality comparability gating."""
    # Test A: Mismatched anatomy
    mismatched_payload = {
        "prior_study": {"text": "CT chest shows 1.5 cm pulmonary nodule."},
        "current_study": {"text": "Ultrasound abdomen shows 2.0 cm hepatic hemangioma liver segment 7."}
    }
    res_mismatch = post_json("/api/v1/evidence/comparability-gate", mismatched_payload)

    log_test(
        "Feature 2.1: Incompatible Anatomy Blocking (Lung vs Liver)",
        res_mismatch.get("decision") == "BLOCKED" and res_mismatch.get("status") == "INCOMPATIBLE_ANATOMICAL_SITE",
        f"Status: {res_mismatch.get('status')} - Correctly blocked false cross-organ comparison"
    )

    # Test B: Incompatible modality (Biopsy vs CT)
    modality_payload = {
        "prior_study": {"text": "Histopathology biopsy specimen reveals adenocarcinoma."},
        "current_study": {"text": "CT scan thorax reveals lung density 2.2 cm."}
    }
    res_modality = post_json("/api/v1/evidence/comparability-gate", modality_payload)

    log_test(
        "Feature 2.2: Incompatible Modality Blocking (Histopathology vs CT)",
        res_modality.get("decision") == "BLOCKED" and res_modality.get("status") == "INCOMPATIBLE_IMAGING_MODALITY",
        f"Status: {res_modality.get('status')} - Blocked non-standard cross-modality RECIST"
    )

    # Test C: Compatible Study Pair
    compatible_payload = {
        "prior_study": {"text": "CT chest axial slice reveals 2.0 cm right lung nodule."},
        "current_study": {"text": "CT chest axial slice reveals 2.5 cm right lung nodule."}
    }
    res_compatible = post_json("/api/v1/evidence/comparability-gate", compatible_payload)
    delta = res_compatible.get("calculated_delta_percent")

    log_test(
        "Feature 2.3: Valid Study Pair Acceptance & Metric Delta",
        res_compatible.get("decision") == "PERMITTED" and delta == 25.0,
        f"Status: {res_compatible.get('status')} - Computed delta: +{delta}% (RECIST progression threshold met)"
    )


def test_feature3_minimum_information_acquisition():
    """Test Feature 3: Information gap ranking and patient burden budget."""
    payload = {
        "report_data": {
            "findings": [{"finding": "Ill-defined 2.8 cm pulmonary mass"}],
            "sections": {"findings": "2.8 cm mass right hilar region"}
        },
        "symptom_data": {
            "symptoms": ["cough"]  # Missing red flag screening & onset duration
        }
    }

    res = post_json("/api/v1/evidence/active-acquisition", payload)
    next_action = res.get("next_action")
    top_gap = res.get("recommended_gap", {})

    log_test(
        "Feature 3.1: Minimum-Information Next Action Optimization",
        next_action in ["INQUIRE_TARGETED_RED_FLAGS", "INQUIRE_SYMPTOM_ONSET"],
        f"Engine selected optimal lowest-burden inquiry: '{next_action}' (Utility: {top_gap.get('utility_score')})"
    )

    # Verify that highly technical questions are NOT dumped onto the patient
    all_gaps = res.get("all_gaps_evaluated", [])
    unsolvable = [g for g in all_gaps if not g.get("patient_solvable")]
    log_test(
        "Feature 3.2: Lay Patient Competence Boundary Enforcement",
        len(unsolvable) > 0 and all(g.get("patient_burden") >= 0.8 for g in unsolvable),
        f"Identified {len(unsolvable)} technical pathology gaps reserved strictly for physician consultation"
    )


def test_feature4_privacy_deidentification():
    """Test Feature 4: Direct identifier stripping with provenance anchor preservation."""
    payload = {
        "document_id": "TEST_DOC_401",
        "text": "Patient Name: Eleanor Vance, MRN: 4892019. Ph: 212-555-0144. DOB: 09/12/1965. Normal bone scan."
    }

    res = post_json("/api/v1/evidence/sanitize", payload)
    sanitized = res.get("sanitized_text", "")
    redacted_count = res.get("redacted_count", 0)
    risk_score = res.get("leakage_risk_score", 1.0)

    log_test(
        "Feature 4.1: Direct PHI Identifier Redaction",
        redacted_count >= 3 and "[REDACTED_NAME_" in sanitized and "[REDACTED_MRN_" in sanitized,
        f"Redacted {redacted_count} PHI tokens with surrogate anchor hashes"
    )

    log_test(
        "Feature 4.2: Zero Downstream PHI Leakage Invariant",
        risk_score == 0.0 and "Eleanor Vance" not in sanitized and "4892019" not in sanitized,
        f"Risk score: {risk_score} (Verified absence of cleartext patient identifiers)"
    )


def test_integrated_6stage_pipeline():
    """Test the sequential 6-stage end-to-end evidence pipeline."""
    payload = {
        "report_data": {
            "report_id": "RPT-INT-001",
            "raw_text": "Patient Name: Arthur Pendelton. High-resolution contrast CT chest shows 1.8 cm nodule.",
            "sections": {
                "technique": "High-resolution contrast enhanced CT chest.",
                "findings": "1.8 cm non-calcified pulmonary nodule right middle lobe.",
                "impression": "Indeterminate pulmonary nodule. Follow-up recommended."
            },
            "findings": [{"finding": "1.8 cm non-calcified pulmonary nodule", "category": "Pulmonary"}]
        },
        "symptom_data": {"symptoms": ["mild shortness of breath"]}
    }

    res = post_json("/api/v1/evidence/pipeline", payload)
    stages = res.get("stages", [])

    log_test(
        "Integrated Pipeline: 6 Sequential Verification Stages Executed",
        len(stages) == 6 and res.get("is_release_authorized") is True,
        f"Pipeline authorized release across stages: {[s.get('stage_id') for s in stages]}"
    )

    log_test(
        "Integrated Pipeline: Mandatory Clinical Non-Diagnostic Disclaimer",
        "does not issue formal oncologic diagnoses" in res.get("clinical_disclaimer", ""),
        "Safety disclaimer attached and verified"
    )


def test_live_controlled_benchmark():
    """Test the full empirical benchmark suite comparing against the 4 baselines."""
    res = get_json("/api/v1/evidence/benchmark")
    summary = res.get("summary", {})
    exp1 = res.get("experiments", {}).get("experiment_1_change_impact", {}).get("metrics", {})
    exp2 = res.get("experiments", {}).get("experiment_2_comparability_gate", {}).get("metrics", {})
    exp3 = res.get("experiments", {}).get("experiment_3_information_acquisition", {}).get("metrics", {})

    log_test(
        "Benchmark Hypothesis 1: 0% Stale Output Rate in PathoGuard vs >35% in Baseline",
        exp1.get("pathoguard_stale_output_rate_percent") == 0.0 and exp1.get("baseline_no_invalidation_stale_rate_percent", 0) >= 35.0,
        f"PathoGuard stale rate: {exp1.get('pathoguard_stale_output_rate_percent')}% vs Baseline: {exp1.get('baseline_no_invalidation_stale_rate_percent')}%"
    )

    log_test(
        "Benchmark Hypothesis 2: Selective Recomputation Computational Savings (>40%)",
        exp1.get("selective_recomputation_savings_percent", 0) >= 40.0,
        f"Achieved {exp1.get('selective_recomputation_savings_percent')}% savings vs Full Recomputation"
    )

    log_test(
        "Benchmark Hypothesis 3: 100% Incompatible Longitudinal Study Rejection",
        exp2.get("pathoguard_incompatible_rejection_rate_percent") == 100.0,
        f"Rejection rate: {exp2.get('pathoguard_incompatible_rejection_rate_percent')}% vs Baseline: {exp2.get('baseline_incompatible_rejection_rate_percent')}%"
    )

    log_test(
        "Benchmark Hypothesis 4: Patient Questionnaire Burden Reduction (>75%)",
        exp3.get("patient_burden_reduction_percent", 0) >= 75.0,
        f"Reduced question burden by {exp3.get('patient_burden_reduction_percent')}% (Active targeted vs static battery)"
    )


if __name__ == "__main__":
    print("\n================ PATHOGUARD-AI PHASE 18: EVIDENCE INTEGRITY TEST SUITE ================")
    try:
        test_feature1_dependency_graph()
        test_feature1_selective_recomputation()
        test_feature2_comparability_gate()
        test_feature3_minimum_information_acquisition()
        test_feature4_privacy_deidentification()
        test_integrated_6stage_pipeline()
        test_live_controlled_benchmark()
        print("\n================ ALL PHASE 18 TESTS PASSED (14/14) ================\n")
    except Exception as e:
        print(f"\n[ERROR] Test execution failed: {e}\n")
        sys.exit(1)
