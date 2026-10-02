"""
Change Detector & Database Audit Test Suite.
"""

import unittest
from crawler.models import ScholarshipRecord
from crawler.change_detector import ChangeDetector
from database.db import Database


class TestChangeDetectorAndDB(unittest.TestCase):
    def setUp(self):
        self.db = Database()

    def test_fingerprint_generation(self):
        r1 = ScholarshipRecord(
            id="s1", slug="s1", name="Scholarship 1", provider="P1",
            source_type="Corporate CSR", official_source_url="https://csr.org",
            amount_details="₹50,000", eligibility_summary="Undergraduate",
            academic_requirements="60%", course_education_level="UG",
            first_discovered_at="2026-10-01", last_crawled_at="2026-10-01",
            last_verified_at="2026-10-01"
        )
        r2 = ScholarshipRecord(
            id="s1", slug="s1", name="Scholarship 1", provider="P1",
            source_type="Corporate CSR", official_source_url="https://csr.org",
            amount_details="₹50,000", eligibility_summary="Undergraduate",
            academic_requirements="60%", course_education_level="UG",
            first_discovered_at="2026-10-01", last_crawled_at="2026-10-01",
            last_verified_at="2026-10-01"
        )
        self.assertEqual(r1.compute_fingerprint(), r2.compute_fingerprint())

        # Mutate amount
        r2.amount_details = "₹75,000"
        self.assertNotEqual(r1.compute_fingerprint(), r2.compute_fingerprint())

    def test_database_metrics_integrity(self):
        metrics = self.db.get_dashboard_metrics()
        self.assertGreaterEqual(metrics["total_discovered"], 20)
        self.assertGreaterEqual(metrics["verified"], 10)
        self.assertGreaterEqual(metrics["source_types_count"], 3)
        self.assertGreaterEqual(metrics["total_changes_logged"], 2)


if __name__ == "__main__":
    unittest.main()
