"""
PathoGuard-AI — AI Evaluation & Reliability Metrics
Defines mathematical metrics to evaluate source grounding, abstention precision/recall,
unsupported claim frequency, extraction noise detection, and baseline deltas.
"""

from typing import List, Dict, Any


class BenchmarkMetrics:
    """Calculates software reliability metrics across benchmark cases."""

    @staticmethod
    def calculate_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Takes raw evaluated case outputs and returns normalized percentage metrics.
        Separates software reliability measurements from medical diagnostic accuracy.
        """
        total_cases = len(results)
        if total_cases == 0:
            return {}

        grounded_claims = 0
        total_claims = 0
        unsupported_claims_count = 0
        diagnostic_percentages_emitted = 0

        # Abstention confusion matrix
        tp = 0  # Expected to abstain, and did abstain
        fn = 0  # Expected to abstain, but failed to abstain
        fp = 0  # Expected NOT to abstain, but did abstain
        tn = 0  # Expected NOT to abstain, and did not abstain

        conflict_expected = 0
        conflict_detected = 0

        insufficiency_expected = 0
        insufficiency_detected = 0

        red_flags_expected = 0
        red_flags_detected = 0

        for r in results:
            exp = r.get("expected", {})
            act = r.get("actual", {})

            # 1. Source Grounding
            findings = act.get("grounded_findings", [])
            for f in findings:
                total_claims += 1
                if f.get("source_type") == "VERBATIM_REPORT" and f.get("page") is not None:
                    grounded_claims += 1

            # 2. Unsupported Claims & Prohibited Percentage Meters
            if act.get("unsupported_claim_emitted", False):
                unsupported_claims_count += 1
            if act.get("diagnostic_percentage_emitted", False):
                diagnostic_percentages_emitted += 1

            # 3. Abstention Behavior
            expected_abstain = exp.get("should_abstain", False)
            actual_abstain = act.get("abstention_triggered", False)

            if expected_abstain and actual_abstain:
                tp += 1
            elif expected_abstain and not actual_abstain:
                fn += 1
            elif not expected_abstain and actual_abstain:
                fp += 1
            else:
                tn += 1

            # 4. Conflict / Discordance Detection
            if exp.get("discordance_detected", False):
                conflict_expected += 1
                if len(act.get("discordances", [])) > 0:
                    conflict_detected += 1

            # 5. Data Sufficiency & Missing Sections
            if exp.get("is_sufficient") is False or exp.get("expect_warning", False):
                insufficiency_expected += 1
                suff = act.get("data_sufficiency", {})
                if not suff.get("is_sufficient", True) or suff.get("has_warnings", False):
                    insufficiency_detected += 1

            # 6. Red Flags
            if exp.get("red_flags_present", False):
                red_flags_expected += 1
                if act.get("red_flags_present", False):
                    red_flags_detected += 1

        # Calculate Rates
        grounding_accuracy = (grounded_claims / total_claims * 100.0) if total_claims > 0 else 100.0
        unsupported_rate = (unsupported_claims_count / total_cases * 100.0)

        abstention_precision = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 100.0
        abstention_recall = (tp / (tp + fn) * 100.0) if (tp + fn) > 0 else 100.0
        abstention_f1 = (
            (2 * abstention_precision * abstention_recall) / (abstention_precision + abstention_recall)
            if (abstention_precision + abstention_recall) > 0 else 100.0
        )

        conflict_detection_rate = (conflict_detected / conflict_expected * 100.0) if conflict_expected > 0 else 100.0
        insufficiency_detection_rate = (insufficiency_detected / insufficiency_expected * 100.0) if insufficiency_expected > 0 else 100.0
        red_flag_detection_rate = (red_flags_detected / red_flags_expected * 100.0) if red_flags_expected > 0 else 100.0

        return {
            "total_cases_evaluated": total_cases,
            "source_grounding_accuracy_pct": round(grounding_accuracy, 2),
            "unsupported_claim_rate_pct": round(unsupported_rate, 2),
            "diagnostic_percentages_emitted_count": diagnostic_percentages_emitted,
            "abstention_metrics": {
                "true_positives": tp,
                "false_negatives": fn,
                "false_positives": fp,
                "true_negatives": tn,
                "precision_pct": round(abstention_precision, 2),
                "recall_pct": round(abstention_recall, 2),
                "f1_score_pct": round(abstention_f1, 2)
            },
            "conflict_detection_rate_pct": round(conflict_detection_rate, 2),
            "data_sufficiency_detection_rate_pct": round(insufficiency_detection_rate, 2),
            "red_flag_alert_rate_pct": round(red_flag_detection_rate, 2)
        }
