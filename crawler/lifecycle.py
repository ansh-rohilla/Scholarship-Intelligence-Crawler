"""
Lifecycle & Expiry Detection Engine.
Calculates status: ACTIVE, EXPIRING_SOON, EXPIRED, REVIEW_REQUIRED, NO_LONGER_VERIFIABLE.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
import re

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}


class LifecycleManager:
    @staticmethod
    def parse_date(date_str: Optional[str]) -> Optional[datetime]:
        """Parses various date string formats safely."""
        if not date_str or not date_str.strip():
            return None

        clean = date_str.strip().lower()

        # Try ISO format
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                pass

        # Regex for '31 August 2026' or '31 Aug 2026'
        match = re.search(r"(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})", clean)
        if match:
            day = int(match.group(1))
            month_str = match.group(2)[:3]
            year = int(match.group(3))
            month = MONTH_MAP.get(month_str)
            if month:
                try:
                    return datetime(year, month, day)
                except ValueError:
                    pass

        return None

    @classmethod
    def evaluate_status(
        cls,
        closing_date_str: Optional[str],
        verification_status: str,
        is_source_reachable: bool = True,
        is_content_removed: bool = False,
        reference_date: Optional[datetime] = None
    ) -> str:
        """
        Determines the current lifecycle status:
        - NO_LONGER_VERIFIABLE: Source unreachable or scheme removed/discontinued
        - EXPIRED: Deadline has passed
        - EXPIRING_SOON: Deadline within 15 days
        - REVIEW_REQUIRED: Verification status is REVIEW_REQUIRED
        - ACTIVE: Verified and open
        """
        if not is_source_reachable or is_content_removed:
            return "NO_LONGER_VERIFIABLE"

        now = reference_date or datetime.now()

        if closing_date_str:
            closing_dt = cls.parse_date(closing_date_str)
            if closing_dt:
                # If deadline has passed
                if closing_dt.date() < now.date():
                    return "EXPIRED"
                # If deadline within 15 days
                if closing_dt.date() <= (now + timedelta(days=15)).date():
                    return "EXPIRING_SOON"

        # Check verification status
        if verification_status == "REVIEW_REQUIRED":
            return "REVIEW_REQUIRED"

        return "ACTIVE"
