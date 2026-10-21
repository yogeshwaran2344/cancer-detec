"""
PathoGuard-AI — Evidence Integrity & Adaptive Reconciliation Endpoints (Phase 18 Core Innovation)
Exposes REST APIs for:
1. Evidence Dependency Mapping & Change Impact (Selective Recomputation)
2. Report Comparability Gating (RECIST / Modality alignment)
3. Minimum-Information Acquisition (Active uncertainty reduction)
4. Privacy-Preserving De-identification
5. Live Controlled Benchmark Evaluation
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
import datetime

from app.services.privacy_filter import PrivacyPreservingFilter
from app.engine.dependency_graph import (
    EvidenceDependencyGraph,
    build_default_evidence_graph,
    NodeStatus
)
from app.engine.comparability_gate import ReportComparabilityGate, ComparabilityStatus
from app.engine.information_acquisition import MinimumInformationAcquisitionEngine
from app.engine.evidence_pipeline import IntegratedEvidencePipeline

router = APIRouter(prefix="/evidence", tags=["Evidence Integrity & Core Innovation"])


@router.post("/pipeline", summary="Execute 6-Stage Integrated Evidence Pipeline")
def run_integrated_pipeline(payload: Dict[str, Any] = Body(...)):
    """
    Executes the sequential 6-stage evidence pipeline:
    [01. Ingestion & PHI Sanitization] -> [02. Comparability Gate] -> [03. Dependency Mapping]
    -> [04. Change Impact Analysis] -> [05. Targeted Recovery] -> [06. Output Release Gate]
    """
    report_data = payload.get("report_data") or payload
    prior_report = payload.get("prior_report_data")
    symptom_data = payload.get("symptom_data")
    simulated_correction = payload.get("simulated_correction")

    result = IntegratedEvidencePipeline.process_evidence_lifecycle(
        report_data=report_data,
        prior_report_data=prior_report,
        symptom_data=symptom_data,
        simulated_correction=simulated_correction
    )
    return result


@router.post("/dependency-graph", summary="Construct Provenance Dependency DAG")
def get_dependency_graph(payload: Dict[str, Any] = Body(...)):
    """
    Builds a fine-grained evidence provenance DAG linking source text fragments,
    extracted findings, and downstream synthesis statements.
    """
    report_data = payload.get("report_data") or payload
    graph = build_default_evidence_graph(report_data)
    return graph.to_dict()


@router.post("/change-impact", summary="Simulate or Apply Evidence Correction with Selective Recompute")
def apply_change_impact(payload: Dict[str, Any] = Body(...)):
    """
    Demonstrates Feature 1: Evidence Change Impact Engine.
    When a source passage changes or OCR is corrected:
    1. Traces exact downstream dependency subgraph.
    2. Invalidates dependent nodes (SUSPENDED_STALE).
    3. Selectively recomputes only affected nodes.
    4. Preserves independent branches without full recompute.
    """
    report_data = payload.get("report_data") or {
        "report_id": "RPT-DEMO",
        "sections": {
            "technique": "High-resolution contrast enhanced chest CT axial slices.",
            "findings": "3.2 cm solitary pulmonary nodule right upper lobe. No mediastinal adenopathy.",
            "impression": "Suspicious right upper lobe pulmonary mass. Specialist biopsy recommended."
        },
        "findings": [
            {"finding": "3.2 cm pulmonary nodule right upper lobe", "category": "Pulmonary"},
            {"finding": "Clear mediastinal lymph nodes", "category": "Lymphatic"}
        ]
    }

    graph = build_default_evidence_graph(report_data)

    target_node = payload.get("node_id", "src_findings")
    new_content = payload.get("new_content", "1.2 cm benign-appearing pulmonary hamartoma right upper lobe.")
    reason = payload.get("reason", "Radiologist re-read / OCR correction")

    if target_node not in graph.nodes:
        raise HTTPException(
            status_code=400,
            detail=f"Target node '{target_node}' not present in evidence graph. Available nodes: {list(graph.nodes.keys())}"
        )

    # Execute selective recomputation
    result = graph.recompute_selective(
        source_node_id=target_node,
        new_source_content=new_content,
        reason=reason
    )

    return {
        "status": "SUCCESS",
        "operation": "SELECTIVE_RECOMPUTATION",
        "target_node": target_node,
        "impact_result": result,
        "updated_graph_summary": {
            "total_nodes": len(graph.nodes),
            "stale_nodes_remaining": len(graph.get_stale_nodes()),
            "nodes": {nid: n.to_dict() for nid, n in graph.nodes.items()}
        },
        "audit_log": graph.audit_log
    }


@router.post("/comparability-gate", summary="Evaluate Report & Finding Comparability")
def evaluate_comparability(payload: Dict[str, Any] = Body(...)):
    """
    Demonstrates Feature 2: Report Comparability Gate.
    Verifies anatomical site, imaging modality, measurement plane, and metric units
    before allowing longitudinal progression/regression analysis.
    """
    prior_study = payload.get("prior_study")
    current_study = payload.get("current_study")

    if not prior_study or not current_study:
        raise HTTPException(
            status_code=400,
            detail="Payload must include both 'prior_study' and 'current_study' objects."
        )

    eval_result = ReportComparabilityGate.evaluate_comparability(
        prior_study=prior_study,
        current_study=current_study
    )
    return eval_result


@router.post("/active-acquisition", summary="Determine Minimum-Burden Next Information Step")
def determine_active_acquisition(payload: Dict[str, Any] = Body(...)):
    """
    Demonstrates Feature 3: Minimum-Information Acquisition Engine.
    Identifies clinical uncertainty gaps and ranks next actions by uncertainty reduction vs patient burden.
    """
    report_data = payload.get("report_data")
    symptom_data = payload.get("symptom_data")
    prior_reports = payload.get("prior_reports")

    recommendation = MinimumInformationAcquisitionEngine.determine_optimal_next_action(
        report_data=report_data,
        symptom_data=symptom_data,
        prior_reports=prior_reports
    )
    return recommendation


@router.post("/sanitize", summary="Privacy-Aware PHI Stripping with Anchor Preservation")
def sanitize_phi(payload: Dict[str, Any] = Body(...)):
    """
    Demonstrates Feature 4: Privacy-Aware Evidence Processing.
    Extracts and strips direct identifiers (names, MRN, phone, address, DOB)
    while maintaining document offset anchors.
    """
    raw_text = payload.get("text", "")
    doc_id = payload.get("document_id", "DOC_SAMPLE")

    res = PrivacyPreservingFilter.sanitize_text(raw_text, document_id=doc_id)
    return res


@router.get("/benchmark", summary="Execute Live Evidence Integrity & Invalidation Benchmark")
def run_live_benchmark():
    """
    Runs the controlled empirical benchmark comparing PathoGuard-AI's Evidence Integrity Engine
    against 4 standard baselines:
    - Baseline 1: Ordinary Summarizer (no provenance tracking)
    - Baseline 2: Full Recomputation (recalculates entire document on any edit)
    - Baseline 3: No Invalidation (stale outputs remain active)
    - Baseline 4: Naive Longitudinal Comparison (compares mismatched anatomy blindly)
    """
    from app.evaluations.benchmark_evidence_integrity import execute_evidence_integrity_benchmark
    benchmark_report = execute_evidence_integrity_benchmark()
    return benchmark_report
