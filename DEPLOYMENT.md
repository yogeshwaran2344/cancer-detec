# PathoGuard-AI — Production Deployment Guide & Runbook

This document details the production deployment architecture, security hardening, database configuration, monitoring, backups, and incident response procedures for PathoGuard-AI.

---

## 1. Production Architecture Overview

```
[Users / Browsers]
       │ (HTTPS / TLS 1.3)
       ▼
[Cloudflare CDN / Nginx Proxy]
       │
       ├───> Static Assets (HTML/CSS/JS)
       │
       └───> /api/v1/ (Reverse Proxy with Rate Limiting & Security Headers)
                 │
                 ▼
     [FastAPI Backend Cluster] (Cloud Run / AWS ECS)
                 │
         ┌───────┴───────┐
         ▼               ▼
[PostgreSQL Database]   [Encrypted Sandbox Storage]
(Cloud SQL / RDS)       (Private Volume / Cloud Storage)
```

### Hosting Tier Comparison & Recommendations

| Tier | Recommended Platform | Monthly Estimated Cost | Characteristics |
|---|---|---|---|
| **Controlled Clinical Pilot** | **Google Cloud Run + Cloud SQL (db-f1-micro)** | **\$25 – \$40 / month** | Serverless autoscaling (0 to N), automatic HTTPS, private VPC connector, zero server maintenance. |
| **Alternative Container** | AWS ECS Fargate + RDS PostgreSQL | \$40 – \$65 / month | Enterprise IAM integration, CloudWatch metrics, ALB SSL termination. |
| **Lightweight Prototype** | Render / Railway Web Service + Managed Postgres | \$15 – \$25 / month | One-click git deploy, built-in TLS, simple environment management. |

---

## 2. Environment Configuration Matrix

| Variable | Development | Staging | Production | Description |
|---|---|---|---|---|
| `ENVIRONMENT` | `development` | `staging` | `production` | Enforces production runtime safeguards and disables debug endpoints. |
| `DEBUG` | `True` | `False` | `False` | Disables traceback exposure in client responses. |
| `ALLOWED_ORIGINS` | `["http://localhost:5500", ...]` | `["https://staging-app.pathoguard.ai"]` | `["https://app.pathoguard.ai"]` | Strict CORS origin restriction. Wildcard `*` is strictly prohibited. |
| `DATABASE_URL` | `sqlite:///data/pathoguard.db` | `postgresql://...staging` | `postgresql://...prod` | Relational database connection string. |
| `SECRET_KEY` | *(dev fallback)* | Secret Manager | Secret Manager | 64-character cryptographically secure token for sessions and signatures. |
| `MAX_UPLOAD_SIZE_BYTES` | `26214400` (25MB) | `26214400` (25MB) | `26214400` (25MB) | Enforces document upload payload ceilings. |

---

## 3. Security Hardening Checklist

1. **Strict Transport Security & HTTPS:**
   - All HTTP traffic automatically redirected to HTTPS (TLS 1.3).
   - Response headers enforce `Strict-Transport-Security: max-age=31536000; includeSubDomains`.
2. **Clickjacking & MIME Protection:**
   - `X-Frame-Options: DENY`
   - `X-Content-Type-Options: nosniff`
   - `X-XSS-Protection: 1; mode=block`
3. **No Unencrypted PHI Storage:**
   - Uploaded documents reside exclusively in isolated local sandbox storage (`/var/data/pathoguard/sandbox`).
   - Files are purged upon user request or session retention expiration.
4. **Principle of Least Privilege:**
   - Docker containers run under unprivileged non-root user `appuser` (UID 1001).

---

## 4. Health, Uptime Monitoring & Probes

The FastAPI backend provides container orchestrator probes:

- **Liveness Probe (`GET /api/v1/health/live`):**
  - Verifies that the Uvicorn worker process is responsive.
  - Used by Kubernetes / Cloud Run to restart frozen containers.
- **Readiness Probe (`GET /api/v1/health/ready`):**
  - Confirms active relational database access (`SELECT 1`).
  - Confirms storage sandbox filesystem write access.
  - Returns `503 Service Unavailable` if storage or database connection fails, removing the instance from traffic routing.

---

## 5. Automated Backups & Disaster Recovery

### Backup Strategy
- **Frequency:** Automated daily cron at 02:00 UTC.
- **Tool:** `python scripts/backup_db.py` (WAL-safe atomic backup with `PRAGMA quick_check` verification).
- **Retention:** Rotates and prunes backups older than 30 days.

### Recovery Runbook
1. Stop running application containers: `docker-compose down`.
2. Verify integrity of latest target backup:
   ```bash
   sqlite3 /var/data/pathoguard/backups/pathoguard_backup_YYYYMMDD_HHMMSS.db "PRAGMA integrity_check;"
   ```
3. Copy restored database to active path:
   ```bash
   cp /var/data/pathoguard/backups/pathoguard_backup_YYYYMMDD_HHMMSS.db /var/data/pathoguard/pathoguard.db
   ```
4. Restart application containers and verify `/api/v1/health/ready`.

---

## 6. Incident Response & Rollback Procedures

### Rollback Workflow
1. Tag previous stable release in container registry: `pathoguard-backend:v1.0.0-stable`.
2. Deploy stable image digest:
   ```bash
   gcloud run deploy pathoguard-backend --image gcr.io/pathoguard-prod/backend:v1.0.0-stable --region us-central1
   ```
3. Verify liveness and run regression test suite:
   ```bash
   python tests/test_phase14_end_to_end_verification.py
   ```
4. If database schema migration failed, execute rollback migration script before traffic routing.
