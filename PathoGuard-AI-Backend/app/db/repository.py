"""
PathoGuard-AI Database Repository
Handles CRUD operations, search, filtering, report comparisons, and authorization checks.
"""

import json
import sqlite3
import datetime
from typing import List, Dict, Any, Optional, Tuple
from app.db.database import get_db


def init_db():
    """Initializes schema and tables if they do not exist."""
    with get_db() as conn:
        # 1. Reports table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                filename TEXT NOT NULL,
                sanitized_filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                size_kb REAL NOT NULL,
                content_type TEXT NOT NULL,
                pages_count INTEGER DEFAULT 1,
                extraction_method TEXT NOT NULL,
                confidence REAL NOT NULL,
                raw_text TEXT NOT NULL,
                sections TEXT NOT NULL,
                findings TEXT NOT NULL,
                extraction_errors TEXT NOT NULL,
                processing_status TEXT NOT NULL,
                is_verified INTEGER DEFAULT 0,
                verified_at TEXT,
                verification_notes TEXT,
                user_id TEXT DEFAULT 'anonymous_local_user'
            );
        """)

        # 2. Assessments table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                assessment_type TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                primary_symptoms TEXT NOT NULL,
                patient_responses TEXT NOT NULL,
                findings TEXT NOT NULL,
                missing_or_conflicting TEXT NOT NULL,
                suggested_next_steps TEXT NOT NULL,
                red_flag_alert INTEGER DEFAULT 0,
                report_id TEXT,
                user_id TEXT DEFAULT 'anonymous_local_user',
                FOREIGN KEY (report_id) REFERENCES reports (id) ON DELETE SET NULL
            );
        """)

        # 3. Create indices for performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_asm_created ON assessments(created_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_asm_type ON assessments(assessment_type);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_asm_user ON assessments(user_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rpt_user ON reports(user_id);")

        # 4. Seed synthetic demonstration records if empty
        cur = conn.execute("SELECT COUNT(*) FROM assessments;")
        if cur.fetchone()[0] == 0:
            seed_synthetic_data(conn)


def seed_synthetic_data(conn: sqlite3.Connection):
    """Populates initial synthetic clinical cases with de-identified sample evidence."""
    # Synthetic Report 1
    rpt1_findings = [
        {
            "id": "p0",
            "section": "technique",
            "title": "Protocol & Modality",
            "finding": "High-resolution helical axial CT thorax without IV contrast.",
            "body": "Volumetric acquisition from lung apices to adrenal bases at 1.25mm slice intervals.",
            "anchor": "p0",
            "verified": True
        },
        {
            "id": "p1",
            "section": "findings",
            "title": "Subpleural Right Lower Lobe Nodule",
            "finding": "6.2 mm non-calcified solid subpleural nodule identified in right lower lobe.",
            "body": "Smooth margins, peripheral parenchyma; no contiguous architectural distortion.",
            "anchor": "p1",
            "verified": True
        }
    ]
    conn.execute("""
        INSERT INTO reports (
            id, created_at, filename, sanitized_filename, file_path, size_kb,
            content_type, pages_count, extraction_method, confidence, raw_text,
            sections, findings, extraction_errors, processing_status, is_verified, user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "RPT-2026-SEED1",
        "2026-10-18T14:30:00",
        "Thoracic_CT_Contrast_2026.pdf",
        "20261018_Thoracic_CT_Contrast_2026.pdf",
        "",
        2450.5,
        "application/pdf",
        1,
        "Digital PDF Parser (pypdf)",
        99.2,
        "EXAMINATION: CHEST COMPUTED TOMOGRAPHY\nTECHNIQUE: High-resolution helical axial CT thorax without IV contrast.\nFINDINGS: 6.2 mm non-calcified solid subpleural nodule in RLL.\nIMPRESSION: Solitary pulmonary nodule; correlate clinically.\nRECOMMENDATIONS: Fleischner protocol interval scan in 12 months.",
        json.dumps({
            "metadata": "De-identified diagnostic study.",
            "technique": "High-resolution helical axial CT thorax without IV contrast.",
            "findings": "6.2 mm non-calcified solid subpleural nodule in RLL.",
            "impression": "Solitary pulmonary nodule; correlate clinically.",
            "recommendations": "Fleischner protocol interval scan in 12 months."
        }),
        json.dumps(rpt1_findings),
        json.dumps([]),
        "verified",
        1,
        "anonymous_local_user"
    ))

    # Synthetic Assessment 1
    conn.execute("""
        INSERT INTO assessments (
            id, created_at, assessment_type, status, summary, primary_symptoms,
            patient_responses, findings, missing_or_conflicting, suggested_next_steps,
            red_flag_alert, report_id, user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "ASM-2026-0941",
        "2026-10-18T14:32:00",
        "Combined Assessment",
        "Assessment summary ready",
        "Thoracic CT reconciled with 5-week progressive dry cough. Symptom vs nodule location discordance noted.",
        json.dumps(["Persistent dry cough", "Mild exertional dyspnea"]),
        json.dumps({
            "primary_symptoms": ["Persistent dry cough", "Mild exertional dyspnea"],
            "onset": "4-6 weeks",
            "trajectory": "Worsening",
            "frequency": "Daily",
            "age_bracket": "45-54",
            "medical_history": ["Seasonal allergies"]
        }),
        json.dumps(rpt1_findings),
        json.dumps([
            {
                "finding_id": "p1",
                "category": "missing_or_conflicting",
                "title": "Symptom vs Anatomy Discordance",
                "description": "Patient reports persistent cough; nodule is peripheral subpleural where cough receptors are sparse.",
                "clinical_note": "Discordance does not indicate malignancy; cough may stem from independent airway etiology."
            }
        ]),
        json.dumps([
            "Review finding with your primary physician or pulmonologist.",
            "Bring the original radiology image disc and this summary to your consultation.",
            "Ask doctor whether spirometry or baseline pulmonary function test is indicated."
        ]),
        0,
        "RPT-2026-SEED1",
        "anonymous_local_user"
    ))

    # Synthetic Assessment 2 (Symptom Questionnaire)
    conn.execute("""
        INSERT INTO assessments (
            id, created_at, assessment_type, status, summary, primary_symptoms,
            patient_responses, findings, missing_or_conflicting, suggested_next_steps,
            red_flag_alert, report_id, user_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        "ASM-2026-0812",
        "2026-10-12T09:15:00",
        "Symptom Questionnaire",
        "Assessment summary ready",
        "Localized left flank soreness following physical exertion; no imaging report linked.",
        json.dumps(["Intermittent flank soreness"]),
        json.dumps({
            "primary_symptoms": ["Intermittent flank soreness"],
            "onset": "1-2 weeks",
            "trajectory": "Stable",
            "frequency": "After activity",
            "age_bracket": "35-44"
        }),
        json.dumps([]),
        json.dumps([]),
        json.dumps([
            "Monitor trajectory over 14 days.",
            "Consult primary care provider if discomfort becomes constant or changes in character."
        ]),
        0,
        None,
        "anonymous_local_user"
    ))


# ==========================================
# ASSESSMENTS CRUD & SEARCH
# ==========================================

def save_assessment_record(data: Dict[str, Any], user_id: str = "anonymous_local_user") -> str:
    """Inserts or updates an assessment record in SQLite."""
    asm_id = data.get("id") or data.get("assessment_id")
    now_iso = data.get("created_at") or data.get("date") or datetime.datetime.now().isoformat()

    primary_syms = data.get("patient_reported", {}).get("primary_symptoms", [])
    if not primary_syms and "primary_symptoms" in data:
        primary_syms = data["primary_symptoms"]

    summary = data.get("summary") or f"Assessment for {len(primary_syms)} reported symptoms"

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO assessments (
                id, created_at, assessment_type, status, summary, primary_symptoms,
                patient_responses, findings, missing_or_conflicting, suggested_next_steps,
                red_flag_alert, report_id, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            asm_id,
            now_iso,
            data.get("assessment_type") or data.get("type", "Clinical Assessment"),
            data.get("status", "Assessment summary ready"),
            summary,
            json.dumps(primary_syms),
            json.dumps(data.get("patient_reported") or data.get("patient_responses", {})),
            json.dumps(data.get("report_findings") or data.get("findings", [])),
            json.dumps(data.get("missing_or_conflicting", [])),
            json.dumps(data.get("suggested_next_steps", [])),
            1 if data.get("red_flag_alert") else 0,
            data.get("associated_report_id") or data.get("report_id"),
            user_id
        ))
    return asm_id


def find_recent_duplicate_assessment(
    primary_symptoms: List[str],
    report_id: Optional[str] = None,
    user_id: str = "anonymous_local_user",
    window_seconds: int = 15
) -> Optional[Dict[str, Any]]:
    """Checks if an identical assessment was submitted within window_seconds to prevent duplicate submissions."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, created_at, primary_symptoms, report_id, user_id
            FROM assessments 
            WHERE user_id = ? 
            ORDER BY created_at DESC LIMIT 5
        """, (user_id,)).fetchall()
        
        now = datetime.datetime.now()
        syms_json = json.dumps(primary_symptoms)

        for row in rows:
            try:
                row_time = datetime.datetime.fromisoformat(row["created_at"])
                delta = abs((now - row_time).total_seconds())
                if delta <= window_seconds:
                    if row["primary_symptoms"] == syms_json and (row["report_id"] == report_id):
                        return get_assessment_record(row["id"], user_id=user_id)
            except Exception:
                continue
    return None


def get_assessment_record(asm_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves an assessment with ownership authorization check."""
    query = "SELECT * FROM assessments WHERE id = ?"
    params = [asm_id]
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    with get_db() as conn:
        row = conn.execute(query, params).fetchone()
        if not row:
            return None

        return {
            "assessment_id": row["id"],
            "id": row["id"],
            "date": row["created_at"],
            "assessment_date": row["created_at"],
            "type": row["assessment_type"],
            "assessment_type": row["assessment_type"],
            "status": row["status"],
            "summary": row["summary"],
            "patient_reported": json.loads(row["patient_responses"]),
            "report_findings": json.loads(row["findings"]),
            "missing_or_conflicting": json.loads(row["missing_or_conflicting"]),
            "suggested_next_steps": json.loads(row["suggested_next_steps"]),
            "red_flag_alert": bool(row["red_flag_alert"]),
            "report_id": row["report_id"],
            "user_id": row["user_id"]
        }


def list_assessment_records(
    assessment_type: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
) -> Tuple[int, List[Dict[str, Any]]]:
    """Queries assessments with filters, text search, pagination, and total count."""
    clauses = ["1=1"]
    params: List[Any] = []

    if user_id:
        clauses.append("user_id = ?")
        params.append(user_id)

    if assessment_type:
        clauses.append("LOWER(assessment_type) LIKE ?")
        params.append(f"%{assessment_type.lower()}%")

    if search:
        clauses.append("(LOWER(id) LIKE ? OR LOWER(summary) LIKE ? OR LOWER(primary_symptoms) LIKE ?)")
        search_param = f"%{search.lower()}%"
        params.extend([search_param, search_param, search_param])

    where_sql = " AND ".join(clauses)

    with get_db() as conn:
        # Count total matching
        count_cur = conn.execute(f"SELECT COUNT(*) FROM assessments WHERE {where_sql};", params)
        total_count = count_cur.fetchone()[0]

        # Fetch records
        query = f"""
            SELECT id, created_at, assessment_type, status, summary, primary_symptoms,
                   findings, report_id, red_flag_alert
            FROM assessments
            WHERE {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
        """
        rows = conn.execute(query, params + [limit, offset]).fetchall()

        items = []
        for r in rows:
            findings_data = json.loads(r["findings"])
            items.append({
                "id": r["id"],
                "date": r["created_at"],
                "type": r["assessment_type"],
                "status": r["status"],
                "summary": r["summary"],
                "findings_count": len(findings_data),
                "report_linked": bool(r["report_id"]),
                "red_flag_alert": bool(r["red_flag_alert"])
            })

        return total_count, items


def delete_assessment_record(asm_id: str, user_id: Optional[str] = None) -> bool:
    """Safely deletes an assessment with ownership verification."""
    query = "DELETE FROM assessments WHERE id = ?"
    params = [asm_id]
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    with get_db() as conn:
        cur = conn.execute(query, params)
        return cur.rowcount > 0


def purge_user_records(user_id: str = "anonymous_local_user") -> int:
    """Permanently purges all user assessments and reports in accordance with privacy retention policy."""
    with get_db() as conn:
        cur1 = conn.execute("DELETE FROM assessments WHERE user_id = ?;", [user_id])
        cur2 = conn.execute("DELETE FROM reports WHERE user_id = ?;", [user_id])
        return cur1.rowcount + cur2.rowcount


# ==========================================
# PREVIOUS-ASSESSMENT COMPARISON ENGINE
# ==========================================

def compare_assessment_records(id_a: str, id_b: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Compares two previous assessments side by side.
    CRITICAL CLINICAL INTEGRITY RULE:
    Explicitly notes: 'Do not interpret wording differences between reports as confirmed disease progression.'
    """
    record_a = get_assessment_record(id_a, user_id)
    record_b = get_assessment_record(id_b, user_id)

    if not record_a or not record_b:
        raise ValueError("One or both requested assessments were not found.")

    # Chronological sort: earlier record vs later record
    earlier, later = sorted([record_a, record_b], key=lambda x: x["date"])

    # Contrast symptoms
    syms_early = set(earlier["patient_reported"].get("primary_symptoms", []))
    syms_late = set(later["patient_reported"].get("primary_symptoms", []))

    new_symptoms = list(syms_late - syms_early)
    resolved_symptoms = list(syms_early - syms_late)
    persistent_symptoms = list(syms_early & syms_late)

    # Contrast findings
    findings_early = earlier.get("report_findings", [])
    findings_late = later.get("report_findings", [])

    return {
        "status": "success",
        "comparison_title": f"Assessment Comparison: {earlier['id']} vs {later['id']}",
        "earlier_assessment": {
            "id": earlier["id"],
            "date": earlier["date"],
            "type": earlier["type"],
            "findings_count": len(findings_early)
        },
        "later_assessment": {
            "id": later["id"],
            "date": later["date"],
            "type": later["type"],
            "findings_count": len(findings_late)
        },
        "symptom_comparison": {
            "persistent_symptoms": persistent_symptoms,
            "new_symptoms": new_symptoms,
            "resolved_symptoms": resolved_symptoms
        },
        "findings_side_by_side": {
            "earlier_findings": findings_early,
            "later_findings": findings_late
        },
        "clinical_progression_notice": (
            "IMPORTANT CLINICAL GUIDANCE: Do not interpret wording differences between reports "
            "as confirmed disease progression. Radiologist descriptions, measuring planes, and institutional wording "
            "routinely vary between examinations. Only direct side-by-side radiologist review of original DICOM image "
            "series can evaluate true temporal stability."
        )
    }


# ==========================================
# REPORTS PERSISTENCE
# ==========================================

def save_report_record(data: Dict[str, Any], user_id: str = "anonymous_local_user") -> str:
    """Saves report metadata, extracted sections, and findings to SQLite."""
    rpt_id = data.get("report_id") or data.get("id")
    now_iso = data.get("created_at") or datetime.datetime.now().isoformat()

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO reports (
                id, created_at, filename, sanitized_filename, file_path, size_kb,
                content_type, pages_count, extraction_method, confidence, raw_text,
                sections, findings, extraction_errors, processing_status, is_verified,
                verified_at, verification_notes, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            rpt_id,
            now_iso,
            data.get("filename", "report.pdf"),
            data.get("sanitized_filename", "report.pdf"),
            data.get("saved_path") or data.get("file_path", ""),
            data.get("size_kb", 0.0),
            data.get("content_type", "application/pdf"),
            data.get("pages_count", 1),
            data.get("extraction_method", "Digital PDF Parser"),
            data.get("confidence", 95.0),
            data.get("raw_text", ""),
            json.dumps(data.get("sections", {})),
            json.dumps(data.get("findings", [])),
            json.dumps(data.get("extraction_errors", [])),
            data.get("processing_status", "needs_review"),
            1 if data.get("is_verified") else 0,
            data.get("verified_at"),
            data.get("verification_notes"),
            user_id
        ))
    return rpt_id


def get_report_record(rpt_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves report from SQLite."""
    query = "SELECT * FROM reports WHERE id = ?"
    params = [rpt_id]
    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    with get_db() as conn:
        row = conn.execute(query, params).fetchone()
        if not row:
            return None

        return {
            "report_id": row["id"],
            "id": row["id"],
            "created_at": row["created_at"],
            "filename": row["filename"],
            "sanitized_filename": row["sanitized_filename"],
            "saved_path": row["file_path"],
            "size_kb": row["size_kb"],
            "content_type": row["content_type"],
            "pages_count": row["pages_count"],
            "extraction_method": row["extraction_method"],
            "confidence": row["confidence"],
            "raw_text": row["raw_text"],
            "sections": json.loads(row["sections"]),
            "findings": json.loads(row["findings"]),
            "extraction_errors": json.loads(row["extraction_errors"]),
            "processing_status": row["processing_status"],
            "is_verified": bool(row["is_verified"]),
            "verified_at": row["verified_at"],
            "verification_notes": row["verification_notes"],
            "user_id": row["user_id"]
        }


def update_report_verification_record(
    rpt_id: str,
    verified_findings: List[Dict[str, Any]],
    raw_text: Optional[str] = None,
    sections: Optional[Dict[str, str]] = None,
    notes: Optional[str] = None,
    user_id: Optional[str] = None
) -> bool:
    """Updates report verification status in SQLite."""
    now_iso = datetime.datetime.now().isoformat()
    with get_db() as conn:
        # Check ownership
        check_q = "SELECT id, raw_text, sections FROM reports WHERE id = ?"
        params = [rpt_id]
        if user_id:
            check_q += " AND user_id = ?"
            params.append(user_id)
        existing = conn.execute(check_q, params).fetchone()
        if not existing:
            return False

        updated_text = raw_text if raw_text is not None else existing["raw_text"]
        updated_sections = json.dumps(sections) if sections is not None else existing["sections"]

        conn.execute("""
            UPDATE reports
            SET is_verified = 1,
                processing_status = 'verified',
                findings = ?,
                raw_text = ?,
                sections = ?,
                verified_at = ?,
                verification_notes = ?
            WHERE id = ?;
        """, (
            json.dumps(verified_findings),
            updated_text,
            updated_sections,
            now_iso,
            notes,
            rpt_id
        ))
        return True
