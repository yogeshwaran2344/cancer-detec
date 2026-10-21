"""
AI Evaluation & Benchmarking API Endpoints
Provides access to versioned benchmark results, adaptive vs baseline comparisons,
and on-demand benchmark execution.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from app.evaluations.benchmark_runner import BenchmarkRunner
from app.schemas.evaluations import BenchmarkResponse

router = APIRouter()


@router.get("/benchmark-latest", response_model=BenchmarkResponse)
def get_latest_benchmark_report() -> BenchmarkResponse:
    """
    Returns the latest versioned AI evaluation report and comparative metrics
    between the Evidence-Gated Adaptive Engine and the Fixed-Question Baseline.
    """
    report = BenchmarkRunner.get_latest_report()
    if not report:
        raise HTTPException(status_code=500, detail="Failed to retrieve benchmark report.")
    return BenchmarkResponse(**report)


@router.post("/run-benchmark", response_model=BenchmarkResponse)
def trigger_benchmark_run() -> BenchmarkResponse:
    """
    Executes a fresh evaluation run across the full synthetic benchmark dataset,
    tests deterministic consistency, and updates persisted report records.
    """
    report = BenchmarkRunner.run_benchmark()
    return BenchmarkResponse(**report)


@router.get("/dataset-info")
def get_benchmark_dataset_info() -> Dict[str, Any]:
    """Returns metadata about the synthetic benchmark dataset."""
    data = BenchmarkRunner.load_dataset()
    return {
        "version": data.get("version"),
        "created_at": data.get("created_at"),
        "description": data.get("description"),
        "total_cases": len(data.get("cases", [])),
        "categories": data.get("dataset_metadata", {}).get("categories", []),
        "synthetic": data.get("dataset_metadata", {}).get("synthetic", True),
        "de_identified": data.get("dataset_metadata", {}).get("de_identified", True)
    }
