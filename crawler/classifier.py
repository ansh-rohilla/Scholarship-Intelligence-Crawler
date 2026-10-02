"""
Source Classifier Module.
Classifies URLs and domains into authoritative primary types vs aggregators.
"""

from urllib.parse import urlparse
from typing import Tuple, Dict, Any
from crawler.config import (
    OFFICIAL_GOV_DOMAINS,
    OFFICIAL_EDU_DOMAINS,
    OFFICIAL_CORPORATE_TRUST_DOMAINS,
    AGGREGATOR_DOMAINS
)


class SourceClassifier:
    """
    Classifies sources according to the assignment requirements:
    1. Government portals (Central/State)
    2. Universities and educational institutions
    3. Corporate CSR programmes
    4. Foundations and trusts
    5. Aggregators / Blogs (must NOT be treated as authoritative!)
    """

    @staticmethod
    def extract_domain(url: str) -> str:
        try:
            parsed = urlparse(url)
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return ""

    @classmethod
    def classify(cls, url: str) -> Dict[str, Any]:
        """
        Returns a classification dict:
        {
            "domain": str,
            "source_type": str,
            "is_official": bool,
            "confidence_tier": str,
            "notes": str
        }
        """
        domain = cls.extract_domain(url)
        url_lower = url.lower()

        # 1. Government checks
        for gov_d in OFFICIAL_GOV_DOMAINS:
            if gov_d in domain or gov_d in url_lower:
                return {
                    "domain": domain,
                    "source_type": "Government (Central/State)",
                    "is_official": True,
                    "confidence_tier": "HIGH_AUTHORITY_GOV",
                    "notes": f"Verified official government domain matching '{gov_d}'"
                }

        # 2. University / Educational Institution checks
        for edu_d in OFFICIAL_EDU_DOMAINS:
            if edu_d in domain or edu_d in url_lower:
                return {
                    "domain": domain,
                    "source_type": "University / Academic Institution",
                    "is_official": True,
                    "confidence_tier": "HIGH_AUTHORITY_EDU",
                    "notes": f"Verified official university domain matching '{edu_d}'"
                }

        # 3. Corporate CSR & Trusts checks
        for corp_d in OFFICIAL_CORPORATE_TRUST_DOMAINS:
            if corp_d in domain or corp_d in url_lower:
                source_type = "Corporate CSR" if ("tatatrusts" not in corp_d and "nsfoundation" not in corp_d and "kcmet" not in corp_d) else "NGO / Trust"
                return {
                    "domain": domain,
                    "source_type": source_type,
                    "is_official": True,
                    "confidence_tier": "HIGH_AUTHORITY_PROVIDER",
                    "notes": f"Verified official provider/trust domain matching '{corp_d}'"
                }

        # 4. Aggregator checks
        for agg_d in AGGREGATOR_DOMAINS:
            if agg_d in domain or agg_d in url_lower:
                return {
                    "domain": domain,
                    "source_type": "Aggregator",
                    "is_official": False,
                    "confidence_tier": "SECONDARY_DISCOVERY_ONLY",
                    "notes": "Secondary discovery source. Must resolve to official source for verification."
                }

        # 5. Default heuristic for other domains
        if domain.endswith(".org") or "trust" in domain or "foundation" in domain:
            return {
                "domain": domain,
                "source_type": "NGO / Trust",
                "is_official": True,
                "confidence_tier": "PROVISIONAL_OFFICIAL",
                "notes": "Non-profit or foundation domain"
            }

        return {
            "domain": domain,
            "source_type": "Unknown / Secondary",
            "is_official": False,
            "confidence_tier": "UNVERIFIED",
            "notes": "Unrecognized domain. Review required."
        }
