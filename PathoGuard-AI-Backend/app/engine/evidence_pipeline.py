"""
PathoGuard-AI — Integrated Evidence Pipeline (The 6-Stage Gate Architecture)
Executes the sequential end-to-end evidence integrity workflow:
[01. Evidence Ingestion]     -> Sanitizes PHI, captures provenance tokens & hashes
[02. Comparability Gate]     -> Evaluates anatomical and modality comparability with prior studies
[03. Dependency Mapping]     -> Builds fine-grained provenance DAG
[04. Change Impact Analysis] -> Detects mutations & invalidates affected downstream subgraphs
[05. Targeted Recovery]      -> Selectively recomputes only invalidated nodes
[06. Output Release Gate]    -> Evaluates clinical abstention & releases verified patient-safe summary
"""

from typing import Dict, List, Any, Optional
import datetime

from app.services.privacy_filter import PrivacyPreservingFilter
from app.engine.comparability_gate import ReportComparabilityGate, ComparabilityStatus
from app.engine.dependency_graph import (
    EvidenceDependencyGraph,
    build_default_evidence_graph,
    NodeStatus
)
from app.engine.information_acquisition import MinimumInformationAcquisitionEngine
from app.engine.abstention_rules import AbstentionEvaluator


class IntegratedEvidencePipeline:
    """
    Orchestrates the 6-stage Evidence Integrity & Adaptive Reconciliation Engine.
    """

    @classmethod
    def process_evidence_lifecycle(
        cls,
        report_data: Dict[str, Any],
        prior_report_data: Optional[Dict[str, Any]] = None,
        symptom_data: Optional[Dict[str, Any]] = None,
        simulated_correction: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pipeline_log = []
        now_ts = datetime.datetime.utcnow().isoformat()

        # ====================================================================
        # STAGE 01: Evidence Ingestion & Privacy Sanitization
        # ====================================================================
        raw_text = report_data.get("raw_text", "")
        doc_id = report_data.get("report_id", "DOC_01")
        privacy_result = PrivacyPreservingFilter.sanitize_text(raw_text, document_id=doc_id)

        stage_01 = {
            "stage_id": "01_EVIDENCE_INGESTION",
            "stage_name": "Privacy-Aware Evidence Ingestion",
            "status": "COMPLETED",
            "redacted_phi_count": privacy_result["redacted_count"],
            "redactions_summary": privacy_result["redactions_summary"],
            "redaction_map_hash": privacy_result["redaction_map_hash"],
            "leakage_risk_score": privacy_result["leakage_risk_score"],
            "timestamp": now_ts
        }
        pipeline_log.append(stage_01)

        # ====================================================================
        # STAGE 02: Comparability Gate (if prior report exists)
        # ====================================================================
        stage_02: Dict[str, Any] = {
            "stage_id": "02_COMPARABILITY_GATE",
            "stage_name": "Report Comparability Evaluation",
            "status": "BYPASSED_NO_PRIOR_STUDY",
            "decision": "STANDALONE_ANALYSIS_ONLY",
            "timestamp": now_ts
        }

        if prior_report_data:
            comp_eval = ReportComparabilityGate.evaluate_comparability(
                prior_study=prior_report_data,
                current_study=report_data
            )
            stage_02.update({
                "status": "EVALUATED",
                "decision": comp_eval["decision"],
                "comparability_status": comp_eval["status"],
                "is_eligible_for_change_analysis": comp_eval["is_eligible_for_change_analysis"],
                "calculated_delta_percent": comp_eval.get("calculated_delta_percent"),
                "clinical_rationale": comp_eval["clinical_rationale"],
                "cautions": comp_eval.get("cautions", [])
            })
        pipeline_log.append(stage_02)

        # ====================================================================
        # STAGE 03: Dependency Mapping (Constructing Provenance DAG)
        # ====================================================================
        graph = build_default_evidence_graph(report_data)
        stage_03 = {
            "stage_id": "03_DEPENDENCY_MAPPING",
            "stage_name": "Fine-Grained Provenance DAG Construction",
            "status": "COMPLETED",
            "total_nodes": len(graph.nodes),
            "stale_nodes_count": len(graph.get_stale_nodes()),
            "timestamp": now_ts
        }
        pipeline_log.append(stage_03)

        # ====================================================================
        # STAGE 04: Change Impact Analysis (Simulated or Real Correction)
        # ====================================================================
        stage_04 = {
            "stage_id": "04_CHANGE_IMPACT_ANALYSIS",
            "stage_name": "Mutation Impact & Dependency Invalidation",
            "status": "NO_MUTATION_DETECTED",
            "timestamp": now_ts
        }

        stage_05 = {
            "stage_id": "05_TARGETED_RECOVERY",
            "stage_name": "Selective Subgraph Recomputation",
            "status": "SKIPPED_GRAPH_PRISTINE",
            "timestamp": now_ts
        }

        if simulated_correction:
            target_node = simulated_correction.get("node_id", "src_findings")
            new_text = simulated_correction.get("new_text", "Updated clinical observation without residual mass.")
            reason = simulated_correction.get("reason", "Patient OCR manual correction")

            # 4. Invalidation
            inv_res = graph.invalidate_subtree(target_node, reason=reason)
            stage_04.update({
                "status": "INVALIDATION_APPLIED",
                "target_node": target_node,
                "invalidated_nodes_count": inv_res.get("invalidated_nodes_count", 0),
                "unaffected_nodes_count": inv_res.get("unaffected_nodes_count", 0),
                "reason": reason
            })

            # 5. Targeted Selective Recomputation
            recomp_res = graph.recompute_selective(
                source_node_id=target_node,
                new_source_content=new_text,
                reason=reason
            )
            stage_05.update({
                "status": "RECOMPUTATION_COMPLETED",
                "recomputed_count": recomp_res.get("recomputed_count", 0),
                "preserved_count": recomp_res.get("preserved_count", 0),
                "savings_percentage": recomp_res.get("savings_percentage", 0.0)
            })

        pipeline_log.append(stage_04)
        pipeline_log.append(stage_05)

        # ====================================================================
        # STAGE 06: Output Release Gate (Clinical Abstention & Safe Presentation)
        # ====================================================================
        # Evaluate clinical safety & abstention
        sections = report_data.get("sections", {})
        findings = report_data.get("findings", [])
        raw_report_text = report_data.get("raw_text", "")

        abstention_eval = AbstentionEvaluator.evaluate_interpretation(
            query="confirm diagnosis or cancer probability",
            report_text=raw_report_text,
            findings=findings
        )
        abstention_needed = abstention_eval.get("should_abstain", False)
        abstention_reason = abstention_eval.get("reason")
        has_stale_nodes = len(graph.get_stale_nodes()) > 0

        # Information Acquisition Recommendation
        next_action_eval = MinimumInformationAcquisitionEngine.determine_optimal_next_action(
            report_data=report_data,
            symptom_data=symptom_data
        )

        can_release = not has_stale_nodes and (stage_02.get("decision") != "BLOCKED" or not prior_report_data)

        stage_06 = {
            "stage_id": "06_OUTPUT_RELEASE_GATE",
            "stage_name": "Output Release & Clinical Abstention Gate",
            "status": "RELEASE_APPROVED" if can_release else "RELEASE_RESTRICTED",
            "abstention_enforced": abstention_needed,
            "abstention_reason": abstention_reason if abstention_needed else None,
            "stale_nodes_detected": has_stale_nodes,
            "comparability_decision": stage_02.get("decision"),
            "next_recommended_acquisition_action": next_action_eval["next_action"],
            "timestamp": now_ts
        }
        pipeline_log.append(stage_06)

        return {
            "report_id": doc_id,
            "pipeline_status": "SUCCESS" if can_release else "RESTRICTED",
            "is_release_authorized": can_release,
            "stages": pipeline_log,
            "dependency_graph_summary": {
                "total_nodes": len(graph.nodes),
                "stale_nodes_count": len(graph.get_stale_nodes()),
                "nodes": {nid: n.to_dict() for nid, n in graph.nodes.items()}
            },
            "comparability_summary": stage_02,
            "next_information_acquisition": next_action_eval,
            "clinical_disclaimer": (
                "PathoGuard-AI is a supportive clinical intelligence demonstration system. "
                "It does not issue formal oncologic diagnoses or replace specialist evaluation."
            )
        }
