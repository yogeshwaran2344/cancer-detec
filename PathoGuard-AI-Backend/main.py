"""
PathoGuard-AI — Clinical Intelligence Backend
FastAPI server providing local document analysis, OCR verification, and symptom reconciliation.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import datetime
import os

from contextlib import asynccontextmanager
from app.core.config import settings
from app.api.v1.api import api_v1_router
from app.api.routes import router as legacy_api_router
from app.db.repository import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and seed initial synthetic data
    init_db()
    yield


# Initialize FastAPI application
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Local privacy sandbox API for radiological report parsing, OCR verification, and evidence reconciliation.",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure CORS with strict allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.ENVIRONMENT in ["production", "staging"]:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# Global Exception Handlers for consistent response format
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "code": exc.status_code,
            "message": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.datetime.now().isoformat()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        field = " -> ".join(str(loc) for loc in err.get("loc", []))
        errors.append(f"{field}: {err.get('msg', 'Invalid input')}")
    return JSONResponse(
        status_code=422,
        content={
            "status": "validation_error",
            "code": 422,
            "message": "Input validation failed for one or more fields.",
            "details": errors,
            "path": request.url.path,
            "timestamp": datetime.datetime.now().isoformat()
        }
    )


# Mount Frontend Application directly
frontend_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "PathoGuard-AI-Frontend"
)
if os.path.exists(frontend_dir):
    app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# Root endpoint — confirms backend is running
@app.get("/")
def read_root():
    return {
        "platform": settings.PROJECT_NAME,
        "status": "Operational",
        "version": settings.VERSION,
        "mode": "Local Clinical Intelligence Sandbox",
        "frontend_url": "/app/",
        "docs_url": "/docs",
        "api_v1": settings.API_V1_STR,
        "timestamp": datetime.datetime.now().isoformat()
    }


# Top-level Health check endpoints for frontend connectivity
@app.get("/health")
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "PathoGuard-Backend",
        "version": settings.VERSION,
        "timestamp": datetime.datetime.now().isoformat()
    }


# Include Versioned API Router (/api/v1)
app.include_router(api_v1_router, prefix=settings.API_V1_STR)

# Include Legacy Router (/api) for backward compatibility
app.include_router(legacy_api_router, prefix="/api")
