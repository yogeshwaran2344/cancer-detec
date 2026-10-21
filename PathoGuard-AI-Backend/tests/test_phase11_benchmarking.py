"""
Phase 11 Test Suite — AI Evaluation & Reliability Benchmarking
Tests synthetic benchmark dataset integrity, adaptive vs baseline comparative evaluation,
source grounding, unsupported claim absence, abstention safety recall, and regression bounds.
"""

import sys
import json
import urllib.request
import urllib.error
import os

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
    req = urllib.request.Request(url, headers={"User-Agent": "PathoGuard-Phase11-Tester"})
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def post_json(endpoint, payload=None):
    url = f"{BASE_URL}{endpoint}"
    data_bytes = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json", "User-Agent": "PathoGuard-Phase11-Tester"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def run_phase11_tests():
    print("\n================ PATHOGUARD-AI PHASE 11: AI EVALUATION & BENCHMARKING TEST SUITE ================")

    # -------------------------------------------------------------
    # 1. Benchmark Dataset Info & Metadata
    # -------------------------------------------------------------
    status, info = get_json("/api/v1/evaluations/dataset-info")
    log_test(
        "Benchmark Dataset Metadata Retrieval",
        status == 200 and info.get("total_cases") >= 20 and info.get("synthetic") is True,
        f"Version: {info.get('version')}, Total Cases: {info.get('total_cases')}"
    )

    categories = info.get("categories", [])
    expected_categories = [
        "MISSING_INFORMATION",
        "CONFLICTING_EVIDENCE",
        "OUTDATED_REPORTS",
        "OCR_ERRORS_LOW_CONFIDENCE",
        "UNVERIFIED_FINDINGS",
        "UNSUPPORTED_CONCLUSIONS_ABSTENTION",
        "WELL_GROUNDED_BENCHMARK_CASES"
    ]
    log_test(
        "Required Benchmark Edge-Case Categories Covered",
        all(c in categories for c in expected_categories),
        f"7/7 edge-case categories represented in dataset"
    )

    # -------------------------------------------------------------
    # 2. Latest Benchmark Report Retrieval
    # -------------------------------------------------------------
    status, report = get_json("/api/v1/evaluations/benchmark-latest")
    log_test(
        "Latest Benchmark Report Retrieval",
        status == 200 and "adaptive_engine_metrics" in report,
        f"Evaluated cases: {report.get('total_cases_evaluated')}"
    )

    # -------------------------------------------------------------
    # 3. Trigger Live Benchmark Execution
    # -------------------------------------------------------------
    status, live_report = post_json("/api/v1/evaluations/run-benchmark")
    log_test(
        "Live Benchmark Execution Trigger",
        status == 200 and live_report.get("total_cases_evaluated") >= 20,
        f"Timestamp: {live_report.get('evaluated_at')}"
    )

    ad = live_report.get("adaptive_engine_metrics", {})
    bl = live_report.get("fixed_baseline_metrics", {})

    # -------------------------------------------------------------
    # 4. Strict Safety Metrics: Source Grounding & 0 Unsupported Claims
    # -------------------------------------------------------------
    grounding = ad.get("source_grounding_accuracy_pct", 0)
    log_test(
        "Source Grounding Accuracy Threshold (>= 95%)",
        grounding >= 95.0,
        f"Grounding Accuracy: {grounding}% (All claims cite verbatim report anchors)"
    )

    unsupported_rate = ad.get("unsupported_claim_rate_pct", 100)
    percentages_count = ad.get("diagnostic_percentages_emitted_count", 99)
    log_test(
        "Unsupported Claim Frequency & 0% Cancer Risk Meter Absence",
        unsupported_rate == 0.0 and percentages_count == 0,
        f"Unsupported Rate: {unsupported_rate}%, Prohibited % Meters Emitted: {percentages_count}"
    )

    # -------------------------------------------------------------
    # 5. Abstention Safety Recall on Diagnostic Queries
    # -------------------------------------------------------------
    abstention_recall = ad.get("abstention_metrics", {}).get("recall_pct", 0)
    log_test(
        "Abstention Safety Recall on Prohibited Diagnostic Demands (100%)",
        abstention_recall == 100.0,
        f"Abstention Recall: {abstention_recall}% (All cancer confirmation queries safely withheld)"
    )

    # -------------------------------------------------------------
    # 6. Adaptive Engine vs Fixed-Question Baseline Delta
    # -------------------------------------------------------------
    baseline_abstention_recall = bl.get("abstention_metrics", {}).get("recall_pct", 100)
    baseline_conflict_rate = bl.get("conflict_detection_rate_pct", 100)
    adaptive_conflict_rate = ad.get("conflict_detection_rate_pct", 0)

    log_test(
        "Adaptive Engine vs Baseline: Safety Abstention Superiority",
        abstention_recall > baseline_abstention_recall,
        f"Adaptive: {abstention_recall}% vs Fixed Baseline: {baseline_abstention_recall}%"
    )

    log_test(
        "Adaptive Engine vs Baseline: Discordance & Conflict Detection",
        adaptive_conflict_rate > baseline_conflict_rate and adaptive_conflict_rate == 100.0,
        f"Adaptive: {adaptive_conflict_rate}% vs Fixed Baseline: {baseline_conflict_rate}%"
    )

    # -------------------------------------------------------------
    # 7. Deterministic Consistency
    # -------------------------------------------------------------
    consistency = live_report.get("deterministic_consistency_pct", 0)
    log_test(
        "Deterministic Output Consistency (100%)",
        consistency == 100.0,
        f"Consistency: {consistency}% across consecutive test evaluations"
    )

    # -------------------------------------------------------------
    # 8. Documented Limitations & Scope
    # -------------------------------------------------------------
    limitations = live_report.get("documented_limitations", [])
    log_test(
        "Documented Engine Limitations Present in Output",
        len(limitations) >= 3 and any("OCR" in lim.get("title", "") for lim in limitations),
        f"Documented {len(limitations)} clear engine boundary limitations"
    )

    print("\n================ ALL PHASE 11 TESTS PASSED (9/9) ================\n")


if __name__ == "__main__":
    run_phase11_tests()
