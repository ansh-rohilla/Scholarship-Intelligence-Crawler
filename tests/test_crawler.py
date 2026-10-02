"""
Comprehensive Test Suite for Scholarship Intelligence Crawler.
Verifies all functional and non-functional requirements from Assignment 2.
"""

import unittest
from crawler.classifier import SourceClassifier
from crawler.extractor import ScholarshipExtractor
from crawler.verifier import VerificationEngine
from crawler.lifecycle import LifecycleManager
from crawler.change_detector import ChangeDetector
from crawler.models import ScholarshipRecord
from database.db import Database
from crawler.engine import CrawlerEngine


class TestScholarshipCrawler(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        self.engine = CrawlerEngine(self.db)

    def test_source_classification(self):
        # 1. Government portal
        res_gov = SourceClassifier.classify("https://scholarships.gov.in/fresh/newstdRegfrmInstruction")
        self.assertEqual(res_gov["source_type"], "Government (Central/State)")
        self.assertTrue(res_gov["is_official"])

        # 2. University portal
        res_edu = SourceClassifier.classify("https://www.iitb.ac.in/academic/scholarships")
        self.assertEqual(res_edu["source_type"], "University / Academic Institution")
        self.assertTrue(res_edu["is_official"])

        # 3. Corporate CSR
        res_corp = SourceClassifier.classify("https://www.reliancefoundation.org/undergraduate-scholarships")
        self.assertEqual(res_corp["source_type"], "Corporate CSR")
        self.assertTrue(res_corp["is_official"])

        # 4. Aggregator / Secondary
        res_agg = SourceClassifier.classify("https://www.buddy4study.com/scholarships")
        self.assertEqual(res_agg["source_type"], "Aggregator")
        self.assertFalse(res_agg["is_official"])

    def test_anti_hallucination_defaults(self):
        """Ensures that when income limit is absent, it returns 'Not specified' and never invents values."""
        text_without_income = "Welcome to the merit scholarship for students admitted in year 2026."
        income_val, evidence = ScholarshipExtractor.extract_income_limit(text_without_income)
        self.assertEqual(income_val, "Not specified")
        self.assertIsNone(evidence)

    def test_verification_engine_threshold(self):
        """Enforces the strict rule: Score >= 95% = VERIFIED, < 95% = REVIEW REQUIRED."""
        self.assertEqual(VerificationEngine.get_verification_status(98.5, True), "VERIFIED")
        self.assertEqual(VerificationEngine.get_verification_status(95.0, True), "VERIFIED")
        self.assertEqual(VerificationEngine.get_verification_status(94.9, True), "REVIEW_REQUIRED")
        self.assertEqual(VerificationEngine.get_verification_status(99.0, False), "REVIEW_REQUIRED")

    def test_lifecycle_expiry_detection(self):
        """Past dates must evaluate to EXPIRED."""
        status_past = LifecycleManager.evaluate_status("31 December 2024", "VERIFIED")
        self.assertEqual(status_past, "EXPIRED")

        status_future = LifecycleManager.evaluate_status("31 December 2027", "VERIFIED")
        self.assertEqual(status_future, "ACTIVE")

    def test_change_detection_audit_trail(self):
        """Verifies that changes produce a ChangeRecord and retain old and new values."""
        existing = {
            "closing_date": "31 October 2025",
            "amount_details": "₹12,000",
            "income_criteria": "₹4,50,000",
            "eligibility_summary": "Original summary",
            "academic_requirements": "Original req",
            "application_url": "https://gov.in",
            "status": "ACTIVE"
        }

        # Create updated record
        updated_record = ScholarshipRecord(
            id="test_sch",
            slug="test-sch",
            name="Test Scheme",
            provider="Test Ministry",
            source_type="Government (Central/State)",
            official_source_url="https://gov.in",
            application_url="https://gov.in",
            amount_details="₹12,000",
            eligibility_summary="Original summary",
            academic_requirements="Original req",
            income_criteria="₹4,50,000",
            course_education_level="Undergraduate",
            closing_date="15 January 2026",  # MODIFIED!
            status="ACTIVE",
            raw_evidence={"closing_date": "Extension circular evidence"},
            first_discovered_at="2026-10-01",
            last_crawled_at="2026-10-02",
            last_verified_at="2026-10-02"
        )

        diffs = ChangeDetector.detect_changes(existing, updated_record)
        self.assertEqual(len(diffs), 1)
        self.assertEqual(diffs[0].field_name, "closing_date")
        self.assertEqual(diffs[0].old_value, "31 October 2025")
        self.assertEqual(diffs[0].new_value, "15 January 2026")
        self.assertEqual(diffs[0].evidence, "Extension circular evidence")


if __name__ == "__main__":
    unittest.main()
