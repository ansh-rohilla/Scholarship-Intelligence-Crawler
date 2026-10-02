-- ====================================================================
-- Atlas Scholarship Intelligence Crawler Database Schema
-- Compatible with SQLite 3
-- ====================================================================

PRAGMA foreign_keys = ON;

-- 1. Main Scholarships Table
CREATE TABLE IF NOT EXISTS scholarships (
    id TEXT PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'Government (Central/State)', 'University', 'Corporate CSR', 'NGO / Trust', 'Aggregator'
    official_source_url TEXT NOT NULL,
    application_url TEXT,
    is_source_official INTEGER NOT NULL DEFAULT 1, -- 1 for True, 0 for False
    amount_details TEXT NOT NULL,
    amount_max_inr REAL DEFAULT 0.0,
    eligibility_summary TEXT NOT NULL,
    academic_requirements TEXT NOT NULL,
    course_education_level TEXT NOT NULL,
    income_criteria TEXT NOT NULL,
    age_criteria TEXT NOT NULL,
    gender_criteria TEXT NOT NULL,
    category_criteria TEXT NOT NULL,
    domicile_state TEXT NOT NULL,
    institution_requirements TEXT NOT NULL,
    opening_date TEXT,
    closing_date TEXT,
    documents_required TEXT, -- JSON array
    selection_process TEXT NOT NULL,
    renewal_requirements TEXT NOT NULL,
    status TEXT NOT NULL, -- 'ACTIVE', 'EXPIRING_SOON', 'EXPIRED', 'REVIEW_REQUIRED', 'NO_LONGER_VERIFIABLE'
    confidence_score REAL NOT NULL, -- 0.0 to 100.0
    verification_status TEXT NOT NULL, -- 'VERIFIED' (>=95.0) or 'REVIEW_REQUIRED' (<95.0)
    confidence_breakdown TEXT NOT NULL, -- JSON detailed scoring breakdown
    raw_evidence TEXT NOT NULL, -- JSON mapping fields to source quotes
    fingerprint TEXT NOT NULL, -- SHA256 of fields for fast change detection
    first_discovered_at TEXT NOT NULL,
    last_crawled_at TEXT NOT NULL,
    last_verified_at TEXT NOT NULL,
    change_count INTEGER NOT NULL DEFAULT 0
);

-- 2. Traceable Field-Level Evidence Table
CREATE TABLE IF NOT EXISTS scholarship_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    extracted_value TEXT NOT NULL,
    evidence_text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    confidence_weight REAL NOT NULL DEFAULT 0.0,
    verified_at TEXT NOT NULL,
    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id) ON DELETE CASCADE
);

-- 3. Change History & Audit Trail Table (Requirement 7)
CREATE TABLE IF NOT EXISTS scholarship_change_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scholarship_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    detected_at TEXT NOT NULL,
    source_url TEXT NOT NULL,
    evidence TEXT,
    crawl_run_id TEXT,
    FOREIGN KEY (scholarship_id) REFERENCES scholarships(id) ON DELETE CASCADE
);

-- 4. Crawl Runs & Orchestration Audit Table (Requirement 6)
CREATE TABLE IF NOT EXISTS crawl_runs (
    id TEXT PRIMARY KEY,
    run_number INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL, -- 'RUNNING', 'COMPLETED', 'FAILED'
    scholarships_discovered INTEGER DEFAULT 0,
    scholarships_verified INTEGER DEFAULT 0,
    scholarships_updated INTEGER DEFAULT 0,
    scholarships_unchanged INTEGER DEFAULT 0,
    scholarships_expired INTEGER DEFAULT 0,
    log_summary TEXT
);

-- 5. Discovered Sources & Seeds Table (Requirement 12)
CREATE TABLE IF NOT EXISTS discovered_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    source_type TEXT NOT NULL,
    is_official INTEGER NOT NULL DEFAULT 0,
    discovery_origin TEXT, -- 'Seed Portal', 'Aggregator Outbound', 'Directory Scrape'
    discovered_at TEXT NOT NULL,
    last_checked_at TEXT,
    http_status INTEGER DEFAULT 200
);

-- Indexes for lightning-fast queries
CREATE INDEX IF NOT EXISTS idx_scholarships_status ON scholarships(status);
CREATE INDEX IF NOT EXISTS idx_scholarships_conf ON scholarships(confidence_score);
CREATE INDEX IF NOT EXISTS idx_scholarships_type ON scholarships(source_type);
CREATE INDEX IF NOT EXISTS idx_scholarships_verif ON scholarships(verification_status);
CREATE INDEX IF NOT EXISTS idx_history_scholarship ON scholarship_change_history(scholarship_id);
CREATE INDEX IF NOT EXISTS idx_evidence_scholarship ON scholarship_evidence(scholarship_id);
