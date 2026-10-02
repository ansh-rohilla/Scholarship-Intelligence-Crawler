"""
Discovery Engine.
Discovers scholarship opportunities dynamically across seed portals, institutional directories,
and resolves primary authoritative sources from secondary aggregators.
"""

from typing import List, Dict, Any, Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

from crawler.classifier import SourceClassifier
from crawler.config import (
    OFFICIAL_GOV_DOMAINS,
    OFFICIAL_EDU_DOMAINS,
    OFFICIAL_CORPORATE_TRUST_DOMAINS,
    AGGREGATOR_DOMAINS
)


class DiscoveryEngine:
    """
    Implements Section 12 dynamic discovery:
    Discovery -> Source Classification -> Authority Resolution -> Queue for Extraction.
    """

    DEFAULT_SEEDS = [
        # Government Central Portals
        {
            "url": "https://scholarships.gov.in",
            "name": "National Scholarship Portal (NSP)",
            "type": "Government (Central)"
        },
        {
            "url": "https://www.education.gov.in/scholarships-education-loan-0",
            "name": "Ministry of Education Scholarship Portal",
            "type": "Government (Central)"
        },
        {
            "url": "https://www.aicte-india.org/schemes/students-development-schemes",
            "name": "AICTE Student Schemes",
            "type": "Government (Central)"
        },
        {
            "url": "https://www.ugc.gov.in/page/Scholarships-and-Fellowships.aspx",
            "name": "UGC Scholarships and Fellowships",
            "type": "Government (Central)"
        },
        # Corporate CSR & Foundations
        {
            "url": "https://www.reliancefoundation.org/undergraduate-scholarships",
            "name": "Reliance Foundation Scholarships",
            "type": "Corporate CSR"
        },
        {
            "url": "https://www.tatatrusts.org/our-work/individual-grants-programme/education-grants",
            "name": "Tata Trusts Education Grants",
            "type": "NGO / Trust"
        },
        # Discovery Hubs / Aggregators (Used for discovering outbound official schemes)
        {
            "url": "https://www.buddy4study.com/scholarships",
            "name": "Buddy4Study Discovery Hub",
            "type": "Aggregator"
        }
    ]

    SCHOLARSHIP_KEYWORDS = [
        "scholarship", "fellowship", "grant", "stipend", "scheme",
        "pragati", "saksham", "ishan", "merit", "means", "post-matric",
        "pre-matric", "aicte", "ugc", "inspire", "csr"
    ]

    @classmethod
    def discover_links_from_html(cls, base_url: str, html_content: str) -> List[Dict[str, Any]]:
        """
        Parses an HTML page, finds scholarship-related links, classifies them,
        and if on an aggregator, resolves outbound links to official domains.
        """
        discovered = []
        seen_urls: Set[str] = set()
        soup = BeautifulSoup(html_content, "lxml")

        base_classification = SourceClassifier.classify(base_url)
        is_base_aggregator = not base_classification["is_official"]

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            anchor_text = a.get_text(separator=" ", strip=True).lower()

            if not href or href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
                continue

            # Resolve absolute URL
            abs_url = urljoin(base_url, href)
            clean_url = abs_url.split("?")[0].rstrip("/")

            if clean_url in seen_urls:
                continue

            seen_urls.add(clean_url)

            # Classify link target
            target_classification = SourceClassifier.classify(clean_url)

            # Check relevance
            matches_keyword = any(k in anchor_text or k in clean_url.lower() for k in cls.SCHOLARSHIP_KEYWORDS)

            # If discovered from an aggregator, look specifically for outbound links to official portals!
            if is_base_aggregator:
                if target_classification["is_official"]:
                    discovered.append({
                        "url": clean_url,
                        "title": anchor_text or a.get("title", ""),
                        "source_type": target_classification["source_type"],
                        "is_official": True,
                        "origin": f"Resolved from Aggregator ({base_url}) to Official Primary Source",
                        "confidence_tier": target_classification["confidence_tier"]
                    })
                elif matches_keyword:
                    discovered.append({
                        "url": clean_url,
                        "title": anchor_text,
                        "source_type": "Aggregator",
                        "is_official": False,
                        "origin": "Aggregator Internal Listing",
                        "confidence_tier": "SECONDARY_DISCOVERY_ONLY"
                    })
            else:
                # Coming from an official portal
                if matches_keyword or target_classification["is_official"]:
                    discovered.append({
                        "url": clean_url,
                        "title": anchor_text or clean_url.split("/")[-1].replace("-", " ").title(),
                        "source_type": target_classification["source_type"],
                        "is_official": target_classification["is_official"],
                        "origin": f"Discovered on Official Portal ({base_url})",
                        "confidence_tier": target_classification["confidence_tier"]
                    })

        return discovered
