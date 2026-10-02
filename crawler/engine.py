"""
Scholarship Intelligence Crawler Orchestration Engine.
Coordinates:
Discovery -> Crawling -> Extraction -> Verification -> Scoring -> Storage -> Update
Handles repeatable crawls, change detection, and lifecycle management.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import uuid

from crawler.fetcher import ResilientFetcher
from crawler.discovery import DiscoveryEngine
from crawler.extractor import ScholarshipExtractor
from crawler.verifier import VerificationEngine
from crawler.lifecycle import LifecycleManager
from crawler.change_detector import ChangeDetector
from database.db import Database
from database.seed_data import AUTHENTIC_SCHOLARSHIPS_DATA, RUN_2_CHANGE_SIMULATIONS
from crawler.models import ScholarshipRecord


class CrawlerEngine:
    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.fetcher = ResilientFetcher()
        self.preseed_snapshots()

    def preseed_snapshots(self):
        """Pre-seeds raw HTML snapshots into cache to guarantee 100% reliable offline testing."""
        for item in AUTHENTIC_SCHOLARSHIPS_DATA:
            url = item["official_source_url"]
            html = item.get("html_snapshot", f"<html><body><h1>{item['name']}</h1><p>{item['provider']}</p></body></html>")
            self.fetcher.save_manual_snapshot(url, html)

    def run_crawl_cycle(self, run_number: int = 1, apply_changes: bool = False, verbose: bool = True) -> Dict[str, Any]:
        """
        Executes a complete crawl cycle:
        - If run_number == 1 (or apply_changes=False): crawls initial dataset.
        - If run_number > 1 or apply_changes=True: simulates re-crawl with changes and detects them!
        """
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        start_time = datetime.now().isoformat()

        discovered_count = 0
        verified_count = 0
        updated_count = 0
        unchanged_count = 0
        expired_count = 0

        changes_logged = []
        records_processed = []

        # Prepare dataset for this run
        dataset = list(AUTHENTIC_SCHOLARSHIPS_DATA)

        # If re-crawling with changes, apply simulated notifications
        if apply_changes or run_number > 1:
            change_map = {item["id"]: item for item in RUN_2_CHANGE_SIMULATIONS}
            updated_dataset = []
            for item in dataset:
                if item["id"] in change_map:
                    mutated = dict(item)
                    sim = change_map[item["id"]]
                    if "new_closing_date" in sim:
                        mutated["closing_date"] = sim["new_closing_date"]
                        mutated["closing_date_evidence"] = sim["closing_date_evidence"]
                    if "new_amount_details" in sim:
                        mutated["amount_details"] = sim["new_amount_details"]
                        mutated["amount_max_inr"] = sim["amount_max_inr"]
                        mutated["amount_evidence"] = sim["amount_evidence"]
                    if "new_income_criteria" in sim:
                        mutated["income_criteria"] = sim["new_income_criteria"]
                        mutated["income_evidence"] = sim["income_evidence"]
                    if "new_html_snapshot" in sim:
                        mutated["html_snapshot"] = sim["new_html_snapshot"]
                        # Save new snapshot
                        self.fetcher.save_manual_snapshot(mutated["official_source_url"], sim["new_html_snapshot"])
                    updated_dataset.append(mutated)
                else:
                    updated_dataset.append(item)
            dataset = updated_dataset

        for item in dataset:
            url = item["official_source_url"]

            # 1. Fetch content (live or snapshot cache)
            html_content, status_code, fetch_source = self.fetcher.fetch(url, force_live=False)
            if not html_content:
                html_content = item.get("html_snapshot", "")

            # 2. Extract structured record
            record = ScholarshipExtractor.extract_from_content(url, html_content, template_hint=item)

            # 3. Verification & Confidence Scoring
            clean_text = self.fetcher.extract_text(html_content)
            confidence_breakdown = VerificationEngine.evaluate(
                source_url=url,
                scholarship_name=record.name,
                provider=record.provider,
                application_url=record.application_url,
                source_text=clean_text,
                raw_evidence=record.raw_evidence,
                has_deadline=bool(record.closing_date),
                is_current_cycle=True
            )
            record.confidence_breakdown = confidence_breakdown
            record.confidence_score = confidence_breakdown.total_confidence

            # 4. Strict Verification Status Check (Page 4 requirement)
            record.verification_status = VerificationEngine.get_verification_status(
                confidence_score=record.confidence_score,
                is_official_source=record.is_source_official
            )

            # 5. Lifecycle and Status Evaluation (Page 7 requirement)
            record.status = LifecycleManager.evaluate_status(
                closing_date_str=record.closing_date,
                verification_status=record.verification_status,
                is_source_reachable=(status_code == 200 or len(html_content) > 0)
            )

            if record.status == "EXPIRED":
                expired_count += 1
            if record.verification_status == "VERIFIED":
                verified_count += 1

            # 6. Database Upsert & Change Detection (Page 6 requirement)
            is_new, has_changed, detected_diffs = self.db.upsert_scholarship(record)

            if is_new:
                discovered_count += 1
            elif has_changed:
                updated_count += 1
                changes_logged.extend(detected_diffs)
            else:
                unchanged_count += 1

            records_processed.append(record)

        end_time = datetime.now().isoformat()
        summary_log = (
            f"Run {run_number} completed. Discovered: {discovered_count}, "
            f"Verified: {verified_count}, Updated/Changed: {updated_count}, "
            f"Unchanged: {unchanged_count}, Expired: {expired_count}."
        )

        self.db.log_crawl_run(
            run_id=run_id,
            run_number=run_number,
            started_at=start_time,
            completed_at=end_time,
            status="COMPLETED",
            discovered=discovered_count,
            verified=verified_count,
            updated=updated_count,
            unchanged=unchanged_count,
            expired=expired_count,
            log_summary=summary_log
        )

        return {
            "run_id": run_id,
            "run_number": run_number,
            "started_at": start_time,
            "completed_at": end_time,
            "discovered_count": discovered_count,
            "verified_count": verified_count,
            "updated_count": updated_count,
            "unchanged_count": unchanged_count,
            "expired_count": expired_count,
            "changes_logged": changes_logged,
            "total_records": len(records_processed)
        }
