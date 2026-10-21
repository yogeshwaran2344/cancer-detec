# ==============================================================================
# PathoGuard-AI Backend Multi-Stage Dockerfile (Production Optimized)
# ==============================================================================

# Stage 1: Build & Dependency Wheel Cache
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final Secure Minimal Runtime
FROM python:3.12-slim as runner

# Metadata labels
LABEL maintainer="PathoGuard Engineering <engineering@pathoguard.ai>"
LABEL version="1.0.0"
LABEL description="PathoGuard Clinical Intelligence Evidence-Gated API"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/home/appuser/.local/bin:$PATH" \
    ENVIRONMENT="production"

# Create unprivileged non-root user and persistent sandbox directories
RUN useradd -m -u 1001 appuser \
    && mkdir -p /var/data/pathoguard/sandbox \
    && mkdir -p /app \
    && chown -R appuser:appuser /var/data/pathoguard /app

# Copy installed python wheels from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

WORKDIR /app
COPY --chown=appuser:appuser . /app

USER appuser

# Expose internal API port
EXPOSE 8000

# Healthcheck targeting readiness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready')" || exit 1

# Launch with Uvicorn worker process
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers"]
