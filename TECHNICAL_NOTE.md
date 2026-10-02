# Technical Note: Autonomous Scholarship Intelligence Crawler
**Project:** Atlas Funding Intelligence Engine (Edxso AI Engineer Internship - Assignment 2)  
**Author:** Ansh Rohilla  
**Repository:** [https://github.com/ansh-rohilla/Scholarship-Intelligence-Crawler](https://github.com/ansh-rohilla/Scholarship-Intelligence-Crawler)  
**Status:** Production-Ready Working System  

---

## 1. System Architecture

The Scholarship Intelligence Crawler is designed as a continuous, feedback-driven pipeline that transforms unstructured web information into standardized, verifiable, and audit-traceable scholarship records for Indian students.

```mermaid
flowchart TD
    subgraph Discovery ["1. Multi-Channel Discovery"]
        Seeds["Seed Portals (.gov.in, .ac.in, CSR)"] --> Crawler
        Aggregators["Aggregators (Buddy4Study, Blogs)"] --> Resolver["Outbound Domain Resolver"]
        Resolver --> Crawler
    end

    subgraph Acquisition ["2. Content Fetching & Resilience"]
        Crawler --> Fetcher["Resilient Fetcher (HTTP + Snapshot Cache)"]
        Fetcher --> RawDOM["Raw HTML DOM & Normalized Text"]
    end

    subgraph Processing ["3. Extraction & Anti-Hallucination"]
        RawDOM --> Classifier["Source Classifier (Gov/Edu/CSR/Trust/Agg)"]
        RawDOM --> Extractor["Structured Schema Extractor"]
        Extractor --> FieldEvidence["Verbatim Field Evidence (DB -> Source -> Quote)"]
    end

    subgraph Intelligence ["4. Verification & Confidence Engine"]
        Classifier --> Verifier["Evidence Scoring Rubric (0 - 100%)"]
        FieldEvidence --> Verifier
        Verifier --> Threshold{"Score >= 95.0% AND Official?"}
        Threshold -- Yes --> Verified["Status: VERIFIED"]
        Threshold -- No --> ReviewReq["Status: REVIEW_REQUIRED"]
    end

    subgraph LifecycleEngine ["5. Lifecycle & Temporal Analysis"]
        Verified --> Lifecycle["Lifecycle Manager (Deadline vs Reference Date)"]
        ReviewReq --> Lifecycle
        Lifecycle --> StatusTag["Tag: ACTIVE / EXPIRING_SOON / EXPIRED / NO_LONGER_VERIFIABLE"]
    end

    subgraph Storage ["6. Audit-Trail Storage & Change Tracking"]
        StatusTag --> HashCheck["SHA-256 Fingerprint Diff"]
        HashCheck -- Match --> Unchanged["Record Unchanged"]
        HashCheck -- Diff --> ChangeDetector["Change Detection Engine"]
        ChangeDetector --> AuditHistory["Write to scholarship_change_history"]
        ChangeDetector --> SQLite["Update Main scholarships Table"]
        Unchanged --> SQLite
    end

    subgraph UI ["7. User Interface"]
        SQLite --> StreamlitApp["Streamlit Interactive Dashboard"]
        SQLite --> CLIDemo["Rich Terminal Demonstration CLI"]
    end
```

The system operates across six decoupled layers:
1. **Discovery & Classification Layer:** Evaluates URLs against verified domain registries (`.gov.in`, `.nic.in`, `.ac.in`, authenticated corporate foundations). Outbound links from aggregators are traversed to resolve the primary official portal.
2. **Resilient Fetching & Snapshot Layer:** Employs an HTTP client with header spoofing, exponential backoff, and local disk-backed HTML snapshot caching for offline auditability.
3. **Structured Extraction Layer:** Employs syntactic and semantic rules to populate a standardized 20+ field Atlas-compatible schema without hallucinating missing attributes.
4. **Algorithmic Verification Layer:** Computes an evidence-based confidence score ($S \in [0, 100]$) without relying on black-box LLM estimations.
5. **Lifecycle & Expiry Layer:** Evaluates temporal validity against closing dates to mark records as `ACTIVE`, `EXPIRING_SOON`, or `EXPIRED`.
6. **Audit & Change Detection Layer:** Retains an immutable history log of all altered fields, capturing the old value, new value, detection timestamp, and official evidence snippet.

---

## 2. Technology Choices & Justification

Per the assignment specification, **no paid APIs or closed scraping services** were used. The entire architecture is built using 100% open-source, free-tier technologies:

| Component | Selected Technology | Technical Justification |
| :--- | :--- | :--- |
| **Language** | Python 3.11+ | High performance, rich ecosystem for web scraping, data modeling, and asynchronous IO. |
| **Parsing & DOM Traversal** | `BeautifulSoup4` + `lxml` | Fast, resilient parsing of non-standard and poorly formatted Indian government web pages. |
| **HTTP Client** | `httpx` & `requests` | Connection pooling, redirect tracking, SSL context customization, and timeout resilience. |
| **Data Validation** | `pydantic v2` | Strong type enforcement, schema validation, and serializable data structures. |
| **Database** | SQLite 3 (`scholarships.db`) | Zero configuration, ACID-compliant, embeddable in Git repository for instant evaluation without external database setup. |
| **Interactive UI** | `Streamlit` | Rapid reactive interface displaying real-time metrics, faceted search, evidence inspection, and re-crawl triggers. |
| **CLI & Terminal Logging** | `rich` | ANSI-colored formatted tables, execution trees, and progress indicators for the demonstration script. |

---

## 3. Discovery Methodology

A primary requirement of the assignment is that **discovery must not be hardcoded to a static list of URLs**. 

The discovery engine operates via a **Three-Tier Discovery Architecture**:
1. **Seed Authority Crawling:** Initialized with high-level institutional directories (e.g., National Scholarship Portal, AICTE Student Development Schemes, UGC Fellowships, Reliance Foundation).
2. **Aggregator Outbound Resolution:** Aggregators (e.g., Buddy4Study, educational blogs) are actively crawled for discovery. When an aggregator page is scraped, the engine identifies outbound links pointing to official institutional domains (`.gov.in`, `.ac.in`, `tatatrusts.org`). The aggregator is **never** treated as the authoritative source; rather, the outbound URL is resolved, queued, and extracted as the primary authority.
3. **Source Classifier (`crawler/classifier.py`):** Every discovered URL is evaluated against domain registries:
   - **Government:** `.gov.in`, `.nic.in`, `scholarships.gov.in`, `aicte-india.org`
   - **Universities:** `.ac.in`, `.edu.in`, `iitb.ac.in`, `du.ac.in`
   - **Corporate CSR / Trusts:** Authenticated corporate charity portals (`reliancefoundation.org`, `tatatrusts.org`, `infosys.org`, `ongcscholar.org`)
   - **Aggregator / Secondary:** Flagged as secondary, capping confidence until primary resolution occurs.

---

## 4. Extraction Methodology

Unstructured HTML and text are converted into a standardized Atlas-compatible schema covering 20+ fields:
- Core identity: `name`, `provider`, `source_type`, `official_source_url`, `application_url`
- Financial terms: `amount_details`, `amount_max_inr`
- Eligibility conditions: `eligibility_summary`, `academic_requirements`, `course_education_level`
- Criteria filters: `income_criteria`, `age_criteria`, `gender_criteria`, `category_criteria`, `domicile_state`, `institution_requirements`
- Timelines & Procedures: `opening_date`, `closing_date`, `documents_required`, `selection_process`, `renewal_requirements`

The extraction pipeline leverages a hybrid strategy of CSS/DOM selectors, semantic text normalization, regular expression patterns for monetary values and dates, and structured metadata mapping.

---

## 5. Verification & Confidence-Score Methodology

### The Critical Rule
> *"Do not ask an LLM to simply generate a confidence number. You must design a methodology that produces the score. A scholarship should only be labelled VERIFIED when the system's confidence is 95% or above. Anything below that should be REVIEW REQUIRED."*

### Mathematical Rubric Formulation
The total confidence score $S \in [0.0, 100.0]$ is computed as the linear sum of five verifiable evidence dimensions:

$$S = S_{\text{domain}} + S_{\text{presence}} + S_{\text{application}} + S_{\text{evidence}} + S_{\text{temporal}}$$

```
┌────────────────────────────────────────────────────────┬───────────────┐
│ Evaluation Factor                                      │ Max Weight    │
├────────────────────────────────────────────────────────┼───────────────┤
│ 1. Official Primary Source Authority (S_domain)        │ 35.0 points   │
│ 2. Direct DOM Content & Title Presence (S_presence)    │ 20.0 points   │
│ 3. Official Application Channel Verification (S_app)   │ 15.0 points   │
│ 4. Grounded Field Evidence Traceability (S_evidence)   │ 15.0 points   │
│ 5. Temporal Currency & Deadline Grounding (S_temporal) │ 15.0 points   │
├────────────────────────────────────────────────────────┼───────────────┤
│ Total Maximum Confidence Score                         │ 100.0 points  │
└────────────────────────────────────────────────────────┴───────────────┘
```

#### Factor Breakdown:
1. **$S_{\text{domain}}$ (Max: 35.0 pts):**
   - Verified Government portal (`.gov.in`, `.nic.in`): **35.0 pts**
   - Accredited University portal (`.ac.in`, `.edu.in`): **35.0 pts**
   - Verified Corporate CSR / Philanthropic Trust portal: **33.5 pts**
   - Secondary Aggregator / Unofficial Blog: **5.0 pts** *(Guarantees aggregators cannot reach the 95% threshold)*.
2. **$S_{\text{presence}}$ (Max: 20.0 pts):**
   - Scholarship title tokens confirmed in page text: up to **12.0 pts**
   - Provider entity referenced in page text: **8.0 pts**
3. **$S_{\text{application}}$ (Max: 15.0 pts):**
   - Direct online application portal on official domain: **15.0 pts**
   - Verified institutional/offline application protocol: **10.0 pts**
   - Missing application path: **0.0 pts**
4. **$S_{\text{evidence}}$ (Max: 15.0 pts):**
   - Financial amount supported by verbatim quote: **5.0 pts**
   - Academic eligibility supported by verbatim quote: **5.0 pts**
   - Income criteria or explicit 'Not specified' confirmed: **5.0 pts**
5. **$S_{\text{temporal}}$ (Max: 15.0 pts):**
   - Deadline extracted and supported by date evidence: **10.0 pts**
   - Active academic cycle confirmed: **5.0 pts**

#### Decision Logic:
- $\text{Status} = \mathbf{VERIFIED} \iff S \ge 95.0 \land \text{IsOfficialSource} = \mathbf{True}$
- $\text{Status} = \mathbf{REVIEW\_REQUIRED} \iff S < 95.0 \lor \text{IsOfficialSource} = \mathbf{False}$

---

## 6. Anti-Hallucination Approach & Traceability

Hallucination in scholarship data can mislead vulnerable students into making life-altering academic decisions. To eliminate hallucinations, the system enforces two core architectural invariants:

### 1. Default to "Not specified"
If an official source document does not mention an income ceiling or age limit, the extractor **strictly sets the field to `"Not specified"`**. The system will never guess, estimate, or hallucinate common figures (such as "₹5 lakh" or "25 years").

### 2. End-to-End Evidence Traceability
Every critical field maintains an unbroken provenance chain:
$$\text{Database} \longrightarrow \text{Official Primary URL} \longrightarrow \text{Verbatim Source Evidence} \longrightarrow \text{Extracted Value}$$

In the database, the `scholarship_evidence` table stores the exact textual excerpt from which each field was derived, along with its source URL and verification timestamp.

---

## 7. Change & Stale-Data Detection

Scholarship guidelines, deadlines, and financial amounts change frequently. The crawler is built as a repeatable state machine that retains historical audit trails.

### Cryptographic Fingerprinting
Each scholarship record generates a SHA-256 fingerprint from its core semantic payload:
$$\text{FP} = \text{SHA256}(\text{Name} \parallel \text{Provider} \parallel \text{Amount} \parallel \text{Eligibility} \parallel \text{Income} \parallel \text{Deadline} \parallel \text{AppURL})$$

### Change Detection Workflow (Run 1 $\rightarrow$ Run 2)
1. On re-crawl, if the SHA-256 fingerprint differs, the record enters the **Change Detector** (`crawler/change_detector.py`).
2. The engine performs a field-level diff against tracked attributes: `closing_date`, `amount_details`, `income_criteria`, `eligibility_summary`, `application_url`.
3. If a difference is detected, the old record is **not blindly overwritten**. An immutable row is inserted into `scholarship_change_history` recording:
   - `scholarship_id`
   - `field_name`
   - `old_value`
   - `new_value`
   - `detected_at`
   - `evidence` (the new official circular or gazette notification excerpt)
4. The main record is updated, and its `change_count` incremented.

### Stale & Expired Scholarship Handling
- **`EXPIRED`:** Parsed `closing_date` < current date.
- **`EXPIRING_SOON`:** Parsed `closing_date` $\le \text{current date} + 15\text{ days}$.
- **`NO_LONGER_VERIFIABLE`:** Source URL returns HTTP 4xx/5xx or official page declares the scheme discontinued.
- **`ACTIVE`:** Open and verified for the current cycle.

---

## 8. Empirical Verification & Minimum Output Audit

The deployed database contains **23 authentic Indian scholarships**, rigorously tested against the assignment requirements:

| Metric Required | Minimum Mandate | Delivered Output | Verification Evidence |
| :--- | :--- | :--- | :--- |
| **Real Scholarships** | 20+ records | **23 records** | 100% genuine Central/State govt, IIT, CSR schemes |
| **Verified Against Primary** | 15+ records | **20 records** | NSP, AICTE, UGC, DST, IITB, IITD, Tata Trusts, Reliance |
| **Confidence $\ge$ 95.0%** | 10+ records | **20 records** | Average system confidence: **97.0%** |
| **Different Source Types** | $\ge$ 3 types | **4 distinct types** | Government, University, Corporate CSR, NGO/Trust |
| **Change Detection Examples** | $\ge$ 2 examples | **3 examples** | NSP deadline extended, Reliance grant increased, IITD income revised |
| **Expired / Stale Detection** | $\ge$ 2 examples | **6 examples** | AICTE Pragati 2024 archive, UGC Ishan Uday past cycle |
| **Review Required (<95%)** | Tested threshold | **3 records** | Demonstrates strict rejection of unverified aggregators |

---

## 9. Conclusion

The Scholarship Intelligence Crawler fulfills all requirements of Assignment 2. It avoids black-box LLM estimations in favor of an evidence-backed scoring algorithm, provides complete provenance tracing from database value to official text, and features a functional Streamlit interface and CLI demonstration tool ready for evaluation.
