"""
Change Detection Engine.
Identifies differences between crawls, prevents destructive overwrites,
and retains immutable audit logs with supporting evidence.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from crawler.models import ScholarshipRecord, ChangeRecord


class ChangeDetector:
    TRACKED_FIELDS = [
        "closing_date",
        "opening_date",
        "amount_details",
        "income_criteria",
        "eligibility_summary",
        "academic_requirements",
        "application_url",
        "status"
    ]

    @classmethod
    def detect_changes(
        cls,
        existing_record: Dict[str, Any],
        new_record: ScholarshipRecord,
        crawl_run_id: Optional[str] = None
    ) -> List[ChangeRecord]:
        """
        Compares existing database record with freshly crawled record.
        Returns a list of ChangeRecord objects for every altered field.
        """
        changes = []
        now_str = datetime.now().isoformat()

        for field in cls.TRACKED_FIELDS:
            old_val = existing_record.get(field)
            new_val = getattr(new_record, field, None)

            old_str = str(old_val).strip() if old_val is not None else ""
            new_str = str(new_val).strip() if new_val is not None else ""

            if old_str != new_str:
                evidence = new_record.raw_evidence.get(field) or f"Field updated during re-crawl from '{old_str}' to '{new_str}'"
                changes.append(ChangeRecord(
                    field_name=field,
                    old_value=old_str,
                    new_value=new_str,
                    detected_at=now_str,
                    source_url=new_record.official_source_url,
                    evidence=evidence,
                    crawl_run_id=crawl_run_id
                ))

        return changes
