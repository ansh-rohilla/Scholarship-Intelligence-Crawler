"""
Database Layer for SQLite storage, audit logs, evidence, and change history.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from crawler.config import DB_PATH, SCHEMA_PATH
from crawler.models import ScholarshipRecord, ConfidenceBreakdown, ChangeRecord


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self):
        """Initializes tables and indexes from schema.sql."""
        if not SCHEMA_PATH.exists():
            raise FileNotFoundError(f"Schema file not found at {SCHEMA_PATH}")

        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()

        with self.get_connection() as conn:
            conn.executescript(schema_sql)

    def upsert_scholarship(self, record: ScholarshipRecord) -> Tuple[bool, bool, List[Dict[str, Any]]]:
        """
        Upserts a scholarship record.
        Returns:
            (is_new: bool, has_changed: bool, detected_changes: List[Dict])
        """
        now_str = datetime.now().isoformat()
        current_fp = record.compute_fingerprint()
        detected_changes = []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scholarships WHERE id = ?", (record.id,))
            existing = cursor.fetchone()

            if existing is None:
                # Completely New Record
                cursor.execute("""
                    INSERT INTO scholarships (
                        id, slug, name, provider, source_type, official_source_url,
                        application_url, is_source_official, amount_details, amount_max_inr,
                        eligibility_summary, academic_requirements, course_education_level,
                        income_criteria, age_criteria, gender_criteria, category_criteria,
                        domicile_state, institution_requirements, opening_date, closing_date,
                        documents_required, selection_process, renewal_requirements,
                        status, confidence_score, verification_status, confidence_breakdown,
                        raw_evidence, fingerprint, first_discovered_at, last_crawled_at,
                        last_verified_at, change_count
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?
                    )
                """, (
                    record.id, record.slug, record.name, record.provider, record.source_type, record.official_source_url,
                    record.application_url, 1 if record.is_source_official else 0, record.amount_details, record.amount_max_inr,
                    record.eligibility_summary, record.academic_requirements, record.course_education_level,
                    record.income_criteria, record.age_criteria, record.gender_criteria, record.category_criteria,
                    record.domicile_state, record.institution_requirements, record.opening_date, record.closing_date,
                    json.dumps(record.documents_required), record.selection_process, record.renewal_requirements,
                    record.status, record.confidence_score, record.verification_status,
                    record.confidence_breakdown.model_dump_json(),
                    json.dumps(record.raw_evidence), current_fp,
                    record.first_discovered_at or now_str, record.last_crawled_at or now_str,
                    record.last_verified_at or now_str, 0
                ))

                # Insert field-level evidence
                for field_name, evidence_text in record.raw_evidence.items():
                    val = getattr(record, field_name, "")
                    cursor.execute("""
                        INSERT INTO scholarship_evidence (
                            scholarship_id, field_name, extracted_value,
                            evidence_text, source_url, confidence_weight, verified_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (record.id, field_name, str(val), evidence_text, record.official_source_url, 10.0, now_str))

                conn.commit()
                return True, False, []

            # Existing record: Check if fingerprint changed or fields changed
            prev_fp = existing["fingerprint"]
            is_changed = False
            fields_to_track = [
                ("closing_date", existing["closing_date"], record.closing_date),
                ("amount_details", existing["amount_details"], record.amount_details),
                ("income_criteria", existing["income_criteria"], record.income_criteria),
                ("eligibility_summary", existing["eligibility_summary"], record.eligibility_summary),
                ("status", existing["status"], record.status),
                ("application_url", existing["application_url"], record.application_url),
            ]

            for fname, old_v, new_v in fields_to_track:
                old_str = str(old_v) if old_v is not None else ""
                new_str = str(new_v) if new_v is not None else ""
                if old_str.strip() != new_str.strip():
                    is_changed = True
                    detected_changes.append({
                        "field_name": fname,
                        "old_value": old_str,
                        "new_value": new_str,
                        "detected_at": now_str,
                        "source_url": record.official_source_url,
                        "evidence": record.raw_evidence.get(fname, f"Updated during re-crawl verification: {new_str}")
                    })

            new_change_count = existing["change_count"] + (1 if is_changed else 0)

            # Update Main Table
            cursor.execute("""
                UPDATE scholarships SET
                    name = ?, provider = ?, source_type = ?, official_source_url = ?,
                    application_url = ?, is_source_official = ?, amount_details = ?, amount_max_inr = ?,
                    eligibility_summary = ?, academic_requirements = ?, course_education_level = ?,
                    income_criteria = ?, age_criteria = ?, gender_criteria = ?, category_criteria = ?,
                    domicile_state = ?, institution_requirements = ?, opening_date = ?, closing_date = ?,
                    documents_required = ?, selection_process = ?, renewal_requirements = ?,
                    status = ?, confidence_score = ?, verification_status = ?, confidence_breakdown = ?,
                    raw_evidence = ?, fingerprint = ?, last_crawled_at = ?,
                    last_verified_at = ?, change_count = ?
                WHERE id = ?
            """, (
                record.name, record.provider, record.source_type, record.official_source_url,
                record.application_url, 1 if record.is_source_official else 0, record.amount_details, record.amount_max_inr,
                record.eligibility_summary, record.academic_requirements, record.course_education_level,
                record.income_criteria, record.age_criteria, record.gender_criteria, record.category_criteria,
                record.domicile_state, record.institution_requirements, record.opening_date, record.closing_date,
                json.dumps(record.documents_required), record.selection_process, record.renewal_requirements,
                record.status, record.confidence_score, record.verification_status,
                record.confidence_breakdown.model_dump_json(),
                json.dumps(record.raw_evidence), current_fp,
                now_str, now_str, new_change_count, record.id
            ))

            # Record change history entries
            for ch in detected_changes:
                cursor.execute("""
                    INSERT INTO scholarship_change_history (
                        scholarship_id, field_name, old_value, new_value,
                        detected_at, source_url, evidence
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.id, ch["field_name"], ch["old_value"], ch["new_value"],
                    ch["detected_at"], ch["source_url"], ch["evidence"]
                ))

            # Update evidence if changed
            if is_changed:
                for field_name, evidence_text in record.raw_evidence.items():
                    val = getattr(record, field_name, "")
                    cursor.execute("""
                        INSERT OR REPLACE INTO scholarship_evidence (
                            scholarship_id, field_name, extracted_value,
                            evidence_text, source_url, confidence_weight, verified_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (record.id, field_name, str(val), evidence_text, record.official_source_url, 10.0, now_str))

            conn.commit()
            return False, is_changed, detected_changes

    def get_all_scholarships(self, search: str = "", status: str = "ALL", source_type: str = "ALL", min_confidence: float = 0.0) -> List[Dict[str, Any]]:
        """Retrieves scholarships with optional search and filters."""
        query = "SELECT * FROM scholarships WHERE 1=1"
        params = []

        if search:
            query += " AND (name LIKE ? OR provider LIKE ? OR eligibility_summary LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])

        if status != "ALL":
            query += " AND status = ?"
            params.append(status)

        if source_type != "ALL":
            query += " AND source_type = ?"
            params.append(source_type)

        if min_confidence > 0:
            query += " AND confidence_score >= ?"
            params.append(min_confidence)

        query += " ORDER BY confidence_score DESC, last_verified_at DESC"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def get_scholarship_by_id(self, scholarship_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scholarships WHERE id = ?", (scholarship_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            # Parse JSON fields
            res["confidence_breakdown"] = json.loads(res["confidence_breakdown"]) if res.get("confidence_breakdown") else {}
            res["raw_evidence"] = json.loads(res["raw_evidence"]) if res.get("raw_evidence") else {}
            res["documents_required"] = json.loads(res["documents_required"]) if res.get("documents_required") else []

            # Fetch change history
            cursor.execute("""
                SELECT * FROM scholarship_change_history
                WHERE scholarship_id = ?
                ORDER BY detected_at DESC
            """, (scholarship_id,))
            res["change_history"] = [dict(r) for r in cursor.fetchall()]

            # Fetch evidence records
            cursor.execute("""
                SELECT * FROM scholarship_evidence
                WHERE scholarship_id = ?
            """, (scholarship_id,))
            res["evidence_records"] = [dict(r) for r in cursor.fetchall()]

            return res

    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Calculates dashboard summary metrics."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scholarships")
            total_discovered = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scholarships WHERE verification_status = 'VERIFIED'")
            verified_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scholarships WHERE verification_status = 'REVIEW_REQUIRED'")
            review_required_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scholarships WHERE status = 'ACTIVE'")
            active_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scholarships WHERE status = 'EXPIRED'")
            expired_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scholarships WHERE status = 'EXPIRING_SOON'")
            expiring_soon_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scholarships WHERE change_count > 0")
            recently_updated = cursor.fetchone()[0]

            cursor.execute("SELECT AVG(confidence_score) FROM scholarships")
            avg_conf = cursor.fetchone()[0] or 0.0

            cursor.execute("SELECT COUNT(DISTINCT source_type) FROM scholarships")
            source_types_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM scholarship_change_history")
            total_changes_logged = cursor.fetchone()[0]

            return {
                "total_discovered": total_discovered,
                "verified": verified_count,
                "review_required": review_required_count,
                "active": active_count,
                "expired": expired_count,
                "expiring_soon": expiring_soon_count,
                "recently_updated": recently_updated,
                "average_confidence": round(avg_conf, 1),
                "source_types_count": source_types_count,
                "total_changes_logged": total_changes_logged
            }

    def log_crawl_run(self, run_id: str, run_number: int, started_at: str, completed_at: str,
                      status: str, discovered: int, verified: int, updated: int,
                      unchanged: int, expired: int, log_summary: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO crawl_runs (
                    id, run_number, started_at, completed_at, status,
                    scholarships_discovered, scholarships_verified, scholarships_updated,
                    scholarships_unchanged, scholarships_expired, log_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (run_id, run_number, started_at, completed_at, status, discovered, verified, updated, unchanged, expired, log_summary))
            conn.commit()

    def get_recent_crawl_runs(self, limit: int = 5) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM crawl_runs ORDER BY started_at DESC LIMIT ?", (limit,))
            return [dict(r) for r in cursor.fetchall()]

    def get_recent_changes(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT h.*, s.name as scholarship_name
                FROM scholarship_change_history h
                JOIN scholarships s ON h.scholarship_id = s.id
                ORDER BY h.detected_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(r) for r in cursor.fetchall()]
