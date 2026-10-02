"""
Data Models for the Atlas Scholarship Intelligence Crawler.
Defines normalized schemas compliant with Atlas specifications.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import hashlib
import json


class ScholarshipEvidence(BaseModel):
    field_name: str
    extracted_value: str
    evidence_text: str
    source_url: str
    confidence_weight: float = 0.0


class ConfidenceBreakdown(BaseModel):
    official_source_score: float = 0.0      # max 35
    content_presence_score: float = 0.0     # max 20
    application_channel_score: float = 0.0  # max 15
    eligibility_grounding_score: float = 0.0 # max 15
    temporal_currency_score: float = 0.0    # max 15
    total_confidence: float = 0.0           # max 100.0
    is_official_source: bool = False
    evidence_notes: List[str] = Field(default_factory=list)


class ChangeRecord(BaseModel):
    field_name: str
    old_value: Optional[str]
    new_value: Optional[str]
    detected_at: str
    source_url: str
    evidence: Optional[str] = None
    crawl_run_id: Optional[str] = None


class ScholarshipRecord(BaseModel):
    id: str
    slug: str
    name: str
    provider: str
    source_type: str  # Government (Central/State), University, Corporate CSR, NGO / Trust, Aggregator
    official_source_url: str
    application_url: Optional[str] = None
    is_source_official: bool = True
    amount_details: str
    amount_max_inr: float = 0.0
    eligibility_summary: str
    academic_requirements: str
    course_education_level: str
    income_criteria: str = "Not specified"
    age_criteria: str = "Not specified"
    gender_criteria: str = "All"
    category_criteria: str = "All"
    domicile_state: str = "All India"
    institution_requirements: str = "Recognized Indian Institutions"
    opening_date: Optional[str] = None
    closing_date: Optional[str] = None
    documents_required: List[str] = Field(default_factory=list)
    selection_process: str = "Merit and Eligibility Criteria"
    renewal_requirements: str = "Subject to satisfactory academic progress"
    status: str = "ACTIVE"  # ACTIVE, EXPIRING_SOON, EXPIRED, REVIEW_REQUIRED, NO_LONGER_VERIFIABLE
    confidence_score: float = 0.0
    verification_status: str = "REVIEW_REQUIRED"  # VERIFIED or REVIEW_REQUIRED
    confidence_breakdown: ConfidenceBreakdown = Field(default_factory=ConfidenceBreakdown)
    raw_evidence: Dict[str, str] = Field(default_factory=dict)
    first_discovered_at: str
    last_crawled_at: str
    last_verified_at: str
    change_count: int = 0

    def compute_fingerprint(self) -> str:
        """Computes a SHA-256 fingerprint of core attributes for change detection."""
        core_data = {
            "name": self.name.strip(),
            "provider": self.provider.strip(),
            "amount_details": self.amount_details.strip(),
            "eligibility_summary": self.eligibility_summary.strip(),
            "income_criteria": self.income_criteria.strip(),
            "closing_date": self.closing_date or "",
            "application_url": self.application_url or "",
            "academic_requirements": self.academic_requirements.strip()
        }
        encoded = json.dumps(core_data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
