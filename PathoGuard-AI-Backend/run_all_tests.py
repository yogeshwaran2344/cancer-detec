"""
PathoGuard-AI Master Test Suite Runner
Discovers and executes all backend verification test suites sequentially.
"""

import sys
import subprocess
from pathlib import Path

# Force UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

TESTS_DIR = Path(__file__).resolve().parent / "tests"
PYTHON_EXE = sys.executable

TEST_SUITES = [
    ("Context Safety & Security (HMAC, Negations, Access Gate)", "test_context_safety_and_security.py"),
    ("Phase 3: Genuine Scan Report & OCR Verification", "test_phase3_reports.py"),
    ("Phase 5: Persistent Database & History Isolation", "test_phase5_database.py"),
    ("Phase 8: AI Report Understanding & Clinical Abstention", "test_phase8_ai_report_understanding.py"),
    ("Phase 11: Safety Benchmarking & Grounding Evaluation", "test_phase11_benchmarking.py"),
    ("Phase 18: Evidence Integrity DAG & Comparability Gate", "test_phase18_evidence_integrity.py"),
    ("API Endpoints & Integration Verification", "test_api_endpoints.py"),
    ("Phase 14: Clinical Safety & End-to-End Workflow Verification", "test_phase14_end_to_end_verification.py")
]

def main():
    print("=" * 80)
    print("        PATHOGUARD-AI COMPREHENSIVE VERIFICATION TEST SUITE RUNNER")
    print("=" * 80)
    print(f"Python Executable: {PYTHON_EXE}")
    print(f"Tests Directory:   {TESTS_DIR}\n")

    passed_suites = 0
    total_suites = len(TEST_SUITES)
    results = []

    for name, filename in TEST_SUITES:
        filepath = TESTS_DIR / filename
        if not filepath.exists():
            print(f"[ERROR] Test file not found: {filename}")
            results.append((name, "MISSING", 1))
            continue

        print(f"\n--- Running: {name} ({filename}) ---")
        res = subprocess.run([PYTHON_EXE, str(filepath)], capture_output=False)
        if res.returncode == 0:
            passed_suites += 1
            results.append((name, "PASSED", 0))
        else:
            results.append((name, "FAILED", res.returncode))

    print("\n" + "=" * 80)
    print("                        TEST RUNNER EXECUTION SUMMARY")
    print("=" * 80)
    for name, status, code in results:
        flag = "[PASS]" if status == "PASSED" else "[FAIL]"
        print(f" {flag} {name:<65} : {status}")

    print("=" * 80)
    print(f"Overall Result: {passed_suites}/{total_suites} test suites passed ({'ALL PASSED' if passed_suites == total_suites else 'FAILURES DETECTED'})")
    print("=" * 80 + "\n")

    sys.exit(0 if passed_suites == total_suites else 1)

if __name__ == "__main__":
    main()
