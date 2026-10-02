"""
Configuration and settings for the Scholarship Intelligence Crawler.
"""

from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_SNAPSHOTS_DIR = DATA_DIR / "raw_snapshots"
DB_PATH = DATA_DIR / "scholarships.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

# Verification & Scoring Thresholds
MIN_CONFIDENCE_FOR_VERIFIED = 95.0  # Strict requirement from assignment (Page 4)
STALE_DAYS_THRESHOLD = 30  # Re-verify if older than 30 days
EXPIRING_SOON_DAYS = 15    # Mark as EXPIRING_SOON if closing within 15 days

# User-Agent headers for realistic HTTP requests
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}

# Domain Classifications
OFFICIAL_GOV_DOMAINS = [
    ".gov.in",
    ".nic.in",
    "scholarships.gov.in",
    "education.gov.in",
    "ugc.gov.in",
    "aicte-india.org",
    "warb-mha.gov.in",
    "online-inspire.gov.in",
    "minorityaffairs.gov.in",
    "socialjustice.gov.in",
    "tribal.nic.in",
    "dst.gov.in",
    "ugcnetonline.in"
]

OFFICIAL_EDU_DOMAINS = [
    ".ac.in",
    ".edu.in",
    "iitb.ac.in",
    "iitd.ac.in",
    "du.ac.in",
    "iitm.ac.in",
    "iitk.ac.in",
    "jnu.ac.in",
    "bhu.ac.in"
]

OFFICIAL_CORPORATE_TRUST_DOMAINS = [
    "tatatrusts.org",
    "reliancefoundation.org",
    "adityabirlacapital.com",
    "hdfcbank.com",
    "ongcscholar.org",
    "infosys.org",
    "kcmet.org",
    "pg.nsfoundation.co.in",
    "nsfoundation.co.in",
    "azimpremjifoundation.org",
    "drreddysfoundation.org"
]

AGGREGATOR_DOMAINS = [
    "buddy4study.com",
    "sarkariresult.com",
    "aglasem.com",
    "collegedunia.com",
    "shiksha.com",
    "careerindia.com",
    "scholarshipsads.com",
    "scholarshipsinindia.com",
    "blogspot.com",
    "wordpress.com"
]
