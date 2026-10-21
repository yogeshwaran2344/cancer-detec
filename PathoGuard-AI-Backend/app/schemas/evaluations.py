"""
Pydantic Schemas for AI Evaluation & Benchmarking
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class AbstentionMetricDetail(BaseModel):
    true_positives: int
    false_negatives: int
    false_positives: int
    true_negatives: int
    precision_pct: float
    recall_pct: float
    f1_score_pct: float


class ModelMetricDetail(BaseModel):
    total_cases_evaluated: int
    source_grounding_accuracy_pct: float
    unsupported_claim_rate_pct: float
    diagnostic_percentages_emitted_count: int
    abstention_metrics: AbstentionMetricDetail
    conflict_detection_rate_pct: float
    data_sufficiency_detection_rate_pct: float
    red_flag_alert_rate_pct: float


class BaselineComparisonItem(BaseModel):
    metric: str
    adaptive_engine: str
    fixed_baseline: str
    advantage: str


class DocumentedLimitation(BaseModel):
    limitation_id: str
    title: str
    description: str
    mitigation: str


class CaseEvaluationSummaryItem(BaseModel):
    case_id: str
    category: str
    title: str
    abstention_triggered: bool
    red_flags: bool
    discordance_count: int
    unverified_findings: int
    passed: bool


class BenchmarkResponse(BaseModel):
    evaluation_title: str
    benchmark_dataset_version: str
    evaluated_at: str
    total_cases_evaluated: int
    deterministic_consistency_pct: float
    adaptive_engine_metrics: ModelMetricDetail
    fixed_baseline_metrics: ModelMetricDetail
    baseline_comparison: Dict[str, BaselineComparisonItem]
    documented_limitations: List[DocumentedLimitation]
    case_evaluations_summary: List[CaseEvaluationSummaryItem]
