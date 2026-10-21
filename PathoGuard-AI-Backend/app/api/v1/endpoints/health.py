"""
Health, Liveness & Readiness Endpoints
Provides lightweight operational status, process liveness, and database/storage readiness checks.
"""

from fastapi import APIRouter, HTTPException
import datetime
import os
from app.core.config import settings
from app.schemas.health import HealthCheckResponse
from app.db.database import get_connection

router = APIRouter()


@router.get("", response_model=HealthCheckResponse)
@router.get("/", response_model=HealthCheckResponse)
def get_health_status() -> HealthCheckResponse:
    """Return health status and environment configuration metadata."""
    return HealthCheckResponse(
        status="healthy",
        service="PathoGuard-Backend",
        version=settings.VERSION,
        timestamp=datetime.datetime.now().isoformat(),
        environment=settings.ENVIRONMENT
    )


@router.get("/live")
def get_liveness_probe():
    """Kubernetes / Cloud Run liveness probe: confirms API process is responsive."""
    return {
        "status": "alive",
        "timestamp": datetime.datetime.now().isoformat()
    }


@router.get("/ready")
def get_readiness_probe():
    """
    Readiness probe: validates SQLite/PostgreSQL connection and sandbox disk availability.
    Fails with 503 if persistent storage or database is unavailable.
    """
    db_ok = False
    storage_ok = False

    # 1. Database check
    try:
        conn = get_connection()
        conn.execute("SELECT 1;").fetchone()
        conn.close()
        db_ok = True
    except Exception as e:
        db_ok = False

    # 2. Upload storage check
    sandbox_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "uploads", "sandbox"
    )
    try:
        os.makedirs(sandbox_dir, exist_ok=True)
        test_file = os.path.join(sandbox_dir, ".health_check.tmp")
        with open(test_file, "w") as f:
            f.write("ok")
        os.remove(test_file)
        storage_ok = True
    except Exception:
        storage_ok = False

    if not db_ok or not storage_ok:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database_accessible": db_ok,
                "storage_sandbox_writable": storage_ok
            }
        )

    return {
        "status": "ready",
        "database_accessible": True,
        "storage_sandbox_writable": True,
        "timestamp": datetime.datetime.now().isoformat()
    }
