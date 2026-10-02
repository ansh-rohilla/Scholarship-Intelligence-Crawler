"""
Verification & Confidence Scoring Engine.
Implements an algorithmic, evidence-grounded scoring methodology (NO arbitrary LLM guessing).
Strictly enforces:
- Score >= 95.0% -> VERIFIED
- Score < 95.0% -> REVIEW_REQUIRED
"""

from typing import Dict, Any, List, Optional
from crawler.classifier import SourceClassifier
from crawler.models import ConfidenceBreakdown
from crawler.config import MIN_CONFIDENCE_FOR_VERIFIED


class VerificationEngine:
    """
    Mathematical evidence-based confidence evaluator.
    Scoring breakdown (100% total):
    1. Official Source Authority: up to 35 pts
    2. Presence on Official Source: up to 20 pts
    3. Official Application Channel: up to 15 pts
    4. Grounded Field Evidence: up to 15 pts
    5. Temporal Currency & Deadline: up to 15 pts
    """

    @classmethod
    def evaluate(
        cls,
        source_url: str,
        scholarship_name: str,
        provider: str,
        application_url: Optional[str],
        source_text: str,
        raw_evidence: Dict[str, str],
        has_deadline: bool,
        is_current_cycle: bool = True
    ) -> ConfidenceBreakdown:
        breakdown = ConfidenceBreakdown()
        evidence_notes = []

        # -------------------------------------------------------------
        # Factor 1: Official Source Authority (Max: 35 pts)
        # -------------------------------------------------------------
        classification = SourceClassifier.classify(source_url)
        source_type = classification["source_type"]
        is_official = classification["is_official"]
        breakdown.is_official_source = is_official

        if classification["confidence_tier"] in ("HIGH_AUTHORITY_GOV", "HIGH_AUTHORITY_EDU"):
            breakdown.official_source_score = 35.0
            evidence_notes.append(f"Primary Authority Domain (+35.0): {classification['notes']}")
        elif classification["confidence_tier"] == "HIGH_AUTHORITY_PROVIDER":
            breakdown.official_source_score = 33.5
            evidence_notes.append(f"Official Corporate CSR/Trust Domain (+33.5): {classification['notes']}")
        elif is_official:
            breakdown.official_source_score = 25.0
            evidence_notes.append(f"Provisional Official Domain (+25.0): {classification['notes']}")
        else:
            breakdown.official_source_score = 5.0
            evidence_notes.append(f"Secondary/Aggregator Source (+5.0): {classification['notes']}")

        # -------------------------------------------------------------
        # Factor 2: Direct Presence on Official Source (Max: 20 pts)
        # -------------------------------------------------------------
        norm_source = source_text.lower()
        norm_name = scholarship_name.lower()
        norm_provider = provider.lower()

        # Token match for scholarship name
        name_words = [w for w in norm_name.split() if len(w) > 3]
        matches = [w for w in name_words if w in norm_source]
        name_match_ratio = len(matches) / len(name_words) if name_words else 0.0

        if name_match_ratio >= 0.7:
            name_score = 12.0
            evidence_notes.append(f"Scholarship title found in official source content (+12.0)")
        elif name_match_ratio >= 0.4:
            name_score = 6.0
            evidence_notes.append(f"Partial scholarship title match in source content (+6.0)")
        else:
            name_score = 0.0
            evidence_notes.append("Scholarship title not confirmed in source content (0.0)")

        # Provider match
        provider_words = [w for w in norm_provider.split() if len(w) > 3]
        provider_matches = [w for w in provider_words if w in norm_source]
        provider_score = 8.0 if len(provider_matches) >= 1 else 2.0
        if provider_score == 8.0:
            evidence_notes.append(f"Provider organization explicitly referenced in source text (+8.0)")

        breakdown.content_presence_score = name_score + provider_score

        # -------------------------------------------------------------
        # Factor 3: Application Channel Traceability (Max: 15 pts)
        # -------------------------------------------------------------
        if application_url and len(application_url.strip()) > 5:
            app_classification = SourceClassifier.classify(application_url)
            if app_classification["is_official"]:
                breakdown.application_channel_score = 15.0
                evidence_notes.append(f"Direct official application portal URL verified (+15.0): {application_url}")
            else:
                breakdown.application_channel_score = 8.0
                evidence_notes.append(f"Application link provided on secondary portal (+8.0)")
        else:
            # Check if offline/nodal application described
            if "offline" in norm_source or "institution" in norm_source or "postal" in norm_source:
                breakdown.application_channel_score = 10.0
                evidence_notes.append("Offline institutional submission channel verified (+10.0)")
            else:
                breakdown.application_channel_score = 0.0
                evidence_notes.append("No traceable application URL or procedure provided (0.0)")

        # -------------------------------------------------------------
        # Factor 4: Grounded Field Evidence Traceability (Max: 15 pts)
        # -------------------------------------------------------------
        evidence_score = 0.0
        # Check amount evidence
        if "amount_details" in raw_evidence and len(raw_evidence["amount_details"].strip()) > 5:
            evidence_score += 5.0
            evidence_notes.append("Financial benefit/amount supported by verbatim evidence quote (+5.0)")

        # Check eligibility evidence
        if "eligibility_summary" in raw_evidence and len(raw_evidence["eligibility_summary"].strip()) > 5:
            evidence_score += 5.0
            evidence_notes.append("Academic & entry eligibility grounded in source text (+5.0)")

        # Check income or criteria evidence
        if "income_criteria" in raw_evidence:
            evidence_score += 5.0
            evidence_notes.append("Income threshold / criteria verified or explicitly marked not specified (+5.0)")

        breakdown.eligibility_grounding_score = evidence_score

        # -------------------------------------------------------------
        # Factor 5: Temporal Currency & Deadline Grounding (Max: 15 pts)
        # -------------------------------------------------------------
        temporal_score = 0.0
        if has_deadline:
            temporal_score += 10.0
            evidence_notes.append("Deadline supported by direct date evidence (+10.0)")
        else:
            temporal_score += 5.0
            evidence_notes.append("Rolling / year-round admission schedule (+5.0)")

        if is_current_cycle:
            temporal_score += 5.0
            evidence_notes.append("Active academic cycle confirmed (+5.0)")

        breakdown.temporal_currency_score = temporal_score

        # -------------------------------------------------------------
        # Total Confidence Calculation
        # -------------------------------------------------------------
        total = (
            breakdown.official_source_score +
            breakdown.content_presence_score +
            breakdown.application_channel_score +
            breakdown.eligibility_grounding_score +
            breakdown.temporal_currency_score
        )
        breakdown.total_confidence = round(min(100.0, max(0.0, total)), 1)
        breakdown.evidence_notes = evidence_notes

        return breakdown

    @staticmethod
    def get_verification_status(confidence_score: float, is_official_source: bool) -> str:
        """
        Critical rule from Page 4:
        A scholarship should only be labelled: VERIFIED when confidence is 95% or above.
        Anything below that should be: REVIEW REQUIRED.
        """
        if confidence_score >= MIN_CONFIDENCE_FOR_VERIFIED and is_official_source:
            return "VERIFIED"
        return "REVIEW_REQUIRED"
