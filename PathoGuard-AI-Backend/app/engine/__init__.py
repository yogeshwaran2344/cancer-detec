"""
PathoGuard-AI Clinical Reasoning & Evidence Understanding Engine
"""

from app.engine.terminology_explainer import (
    explain_medical_term,
    extract_and_explain_terms_in_text,
    CLINICAL_GLOSSARY
)
from app.engine.abstention_rules import AbstentionEvaluator
from app.engine.report_explainer import ReportUnderstandingEngine
from app.engine.adaptive_engine import AdaptiveAssessmentEngine, FixedQuestionBaseline
from app.engine.dependency_graph import (
    EvidenceDependencyGraph,
    DependencyNodeType,
    NodeStatus,
    build_default_evidence_graph
)
from app.engine.comparability_gate import ReportComparabilityGate, ComparabilityStatus
from app.engine.information_acquisition import MinimumInformationAcquisitionEngine, InformationGap
from app.engine.evidence_pipeline import IntegratedEvidencePipeline

__all__ = [
    "explain_medical_term",
    "extract_and_explain_terms_in_text",
    "CLINICAL_GLOSSARY",
    "AbstentionEvaluator",
    "ReportUnderstandingEngine",
    "AdaptiveAssessmentEngine",
    "FixedQuestionBaseline",
    "EvidenceDependencyGraph",
    "DependencyNodeType",
    "NodeStatus",
    "build_default_evidence_graph",
    "ReportComparabilityGate",
    "ComparabilityStatus",
    "MinimumInformationAcquisitionEngine",
    "InformationGap",
    "IntegratedEvidencePipeline"
]
