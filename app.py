"""
Scholarship Intelligence Dashboard - Atlas Prototype.
Streamlit application implementing Section 10 of Assignment 2:
- Summary Intelligence Metrics
- Searchable & Filterable Scholarship Directory
- In-depth Scholarship Details & Verification Audit
- Transparent 'Why this score?' Confidence Breakdown
- Field-level Verbatim Source Evidence
- Full Change Detection History & Audit Trail
- Live Crawler & Re-Crawl Simulation Triggers
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from database.db import Database
from crawler.engine import CrawlerEngine

# Set page config
st.set_page_config(
    page_title="Scholarship Intelligence Engine | Atlas Prototype",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #4B5563;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .badge-verified {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-review {
        background-color: #FEF08A;
        color: #854D0E;
        padding: 4px 10px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.8rem;
    }
    .badge-active {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
    }
    .badge-expired {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
    }
    .evidence-quote {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        padding: 10px 14px;
        font-style: italic;
        margin: 6px 0;
        border-radius: 0 6px 6px 0;
    }
</style>
""", unsafe_allow_html=True)

# Helpers for full-width components across different Streamlit versions
import inspect
def _fw():
    sig = inspect.signature(st.button).parameters
    return {"width": "stretch"} if "width" in sig else {"use_container_width": True}

def _fw_df():
    sig = inspect.signature(st.dataframe).parameters
    return {"width": "stretch"} if "width" in sig else {"use_container_width": True}

# Initialize Database
db = Database()
metrics = db.get_dashboard_metrics()

# Auto-seed if database is empty on fresh cloud deployment
if metrics["total_discovered"] == 0:
    engine = CrawlerEngine(db)
    engine.run_crawl_cycle(run_number=1, apply_changes=False)
    metrics = db.get_dashboard_metrics()

# Header
st.markdown('<div class="main-header">🎓 Scholarship Intelligence Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Atlas Prototype: Autonomous Discovery, Verification, Anti-Hallucination & Change Tracking for Indian Scholarships</div>', unsafe_allow_html=True)

# Sidebar Controls & Actions
with st.sidebar:
    st.image("https://img.icons8.com/color/96/graduation-cap.png", width=64)
    st.title("Crawler Control")
    st.info("System adheres strictly to: Confidence ≥ 95% = VERIFIED. No blackbox LLM confidence numbers.")

    st.subheader("Manual Pipeline Actions")
    if st.button("🚀 Run Initial Crawl (Run 1)", type="primary", **_fw()):
        with st.spinner("Executing crawl run cycle 1..."):
            engine = CrawlerEngine(db)
            res = engine.run_crawl_cycle(run_number=1, apply_changes=False)
            st.success(f"Run 1 completed! Discovered: {res['discovered_count']}, Verified: {res['verified_count']}")
            st.rerun()

    if st.button("⚡ Simulate Re-Crawl (Run 2: Change Detection)", **_fw()):
        with st.spinner("Running re-crawl with updated notices and senate resolutions..."):
            engine = CrawlerEngine(db)
            res = engine.run_crawl_cycle(run_number=2, apply_changes=True)
            st.success(f"Run 2 completed! Detected {res['updated_count']} changes across active schemes.")
            st.rerun()

    st.divider()
    st.subheader("Filter Directory")
    search_query = st.text_input("🔍 Search Scholarships", placeholder="e.g. AICTE, NSP, IIT, Medical...")
    status_filter = st.selectbox(
        "Lifecycle Status",
        options=["ALL", "ACTIVE", "EXPIRING_SOON", "EXPIRED", "REVIEW_REQUIRED", "NO_LONGER_VERIFIABLE"],
        index=0
    )
    source_type_filter = st.selectbox(
        "Source Authority Type",
        options=["ALL", "Government (Central/State)", "University / Academic Institution", "Corporate CSR", "NGO / Trust", "Aggregator"],
        index=0
    )
    min_confidence = st.slider("Minimum Confidence (%)", min_value=0.0, max_value=100.0, value=0.0, step=5.0)

# Render Metric Cards (Section 10 Requirement)
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
with c1:
    st.metric("Total Discovered", metrics["total_discovered"])
with c2:
    st.metric("Verified (≥95%)", metrics["verified"])
with c3:
    st.metric("Review Required", metrics["review_required"])
with c4:
    st.metric("Active Schemes", metrics["active"])
with c5:
    st.metric("Expired / Stale", metrics["expired"])
with c6:
    st.metric("Recently Updated", metrics["recently_updated"])
with c7:
    st.metric("Avg Confidence", f"{metrics['average_confidence']}%")

st.divider()

# Tabs: Directory, Change History, Crawl Runs
tab_directory, tab_history, tab_runs, tab_methodology = st.tabs([
    "📋 Scholarship Directory",
    "🚨 Change Detection Audit",
    "⚙️ Crawl Logs & Runs",
    "📖 Verification Methodology"
])

# -----------------------------------------------------------------------------
# TAB 1: SCHOLARSHIP DIRECTORY & DETAILS
# -----------------------------------------------------------------------------
with tab_directory:
    scholarships = db.get_all_scholarships(
        search=search_query,
        status=status_filter,
        source_type=source_type_filter,
        min_confidence=min_confidence
    )

    st.write(f"Showing **{len(scholarships)}** scholarship records matching criteria:")

    if not scholarships:
        st.warning("No scholarships found matching current filters.")
    else:
        # Display side-by-side or master-detail
        col_list, col_detail = st.columns([1.1, 1.9])

        with col_list:
            selected_id = None
            # Radio or selector list
            options = {s["id"]: f"{s['name'][:42]}... ({s['confidence_score']}%)" if len(s['name']) > 42 else f"{s['name']} ({s['confidence_score']}%)" for s in scholarships}
            selected_id = st.radio("Select a scholarship to inspect details & evidence:", options=list(options.keys()), format_func=lambda x: options[x])

        with col_detail:
            if selected_id:
                s = db.get_scholarship_by_id(selected_id)
                if s:
                    # Top badges
                    b_verif = "badge-verified" if s["verification_status"] == "VERIFIED" else "badge-review"
                    b_stat = "badge-active" if s["status"] == "ACTIVE" else "badge-expired"
                    
                    st.markdown(f"### {s['name']}")
                    st.markdown(
                        f"<span class='{b_verif}'>{s['verification_status']} ({s['confidence_score']}%)</span> "
                        f"<span class='{b_stat}'>Status: {s['status']}</span> "
                        f"<span style='background:#F3F4F6; padding:3px 8px; border-radius:6px; font-size:0.75rem;'>Type: {s['source_type']}</span>",
                        unsafe_allow_html=True
                    )
                    st.write("")

                    # Quick Metadata Table
                    meta_col1, meta_col2 = st.columns(2)
                    with meta_col1:
                        st.markdown(f"**🏛 Provider:** {s['provider']}")
                        st.markdown(f"**💰 Benefit / Amount:** {s['amount_details']}")
                        st.markdown(f"**📅 Closing Deadline:** `{s['closing_date'] or 'Rolling / Open'}`")
                        st.markdown(f"**🎓 Education Level:** {s['course_education_level']}")
                    with meta_col2:
                        st.markdown(f"**💵 Income Limit:** `{s['income_criteria']}`")
                        st.markdown(f"**👥 Category:** {s['category_criteria']}")
                        st.markdown(f"**🚻 Gender:** {s['gender_criteria']}")
                        st.markdown(f"**📍 Domicile:** {s['domicile_state']}")

                    # Action Buttons for URLs
                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        if s["official_source_url"]:
                            st.link_button("🌐 Open Official Primary Source", s["official_source_url"], **_fw())
                    with btn_c2:
                        if s["application_url"]:
                            st.link_button("📝 Open Official Application Portal", s["application_url"], **_fw())

                    st.markdown("---")

                    # Why this score? Section (Assignment Requirement Page 8 & 9)
                    st.subheader("🎯 Why this score? (Algorithmic Confidence Breakdown)")
                    breakdown = s.get("confidence_breakdown", {})
                    
                    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
                    with sc1:
                        st.caption("Official Domain")
                        st.progress(min(1.0, breakdown.get("official_source_score", 0) / 35.0))
                        st.write(f"**{breakdown.get('official_source_score', 0)}/35**")
                    with sc2:
                        st.caption("DOM Presence")
                        st.progress(min(1.0, breakdown.get("content_presence_score", 0) / 20.0))
                        st.write(f"**{breakdown.get('content_presence_score', 0)}/20**")
                    with sc3:
                        st.caption("Application Portal")
                        st.progress(min(1.0, breakdown.get("application_channel_score", 0) / 15.0))
                        st.write(f"**{breakdown.get('application_channel_score', 0)}/15**")
                    with sc4:
                        st.caption("Grounded Evidence")
                        st.progress(min(1.0, breakdown.get("eligibility_grounding_score", 0) / 15.0))
                        st.write(f"**{breakdown.get('eligibility_grounding_score', 0)}/15**")
                    with sc5:
                        st.caption("Temporal Currency")
                        st.progress(min(1.0, breakdown.get("temporal_currency_score", 0) / 15.0))
                        st.write(f"**{breakdown.get('temporal_currency_score', 0)}/15**")

                    if breakdown.get("evidence_notes"):
                        with st.expander("View Itemized Confidence Rubric & Notes", expanded=False):
                            for note in breakdown["evidence_notes"]:
                                st.markdown(f"- {note}")

                    # Verbatim Source Evidence (Traceability: DB -> Source -> Evidence -> Extracted Value)
                    st.subheader("🔍 Source Evidence & Anti-Hallucination Traceability")
                    raw_ev = s.get("raw_evidence", {})
                    if raw_ev:
                        for field_name, quote in raw_ev.items():
                            st.markdown(f"**{field_name.replace('_', ' ').title()}:**")
                            st.markdown(f"<div class='evidence-quote'>\"{quote}\"</div>", unsafe_allow_html=True)
                    else:
                        st.info("No raw evidence quotes recorded.")

                    # Change History for this scholarship
                    st.subheader("📜 Change History & Audit Log")
                    ch_list = s.get("change_history", [])
                    if ch_list:
                        for ch in ch_list:
                            st.warning(
                                f"**CHANGE DETECTED on `{ch['field_name']}`** ({ch['detected_at'][:19]})\n\n"
                                f"- **Previous Value:** `{ch['old_value']}`\n"
                                f"- **New Value:** `{ch['new_value']}`\n"
                                f"- **Evidence:** *{ch['evidence']}*"
                            )
                    else:
                        st.caption("No changes detected since initial baseline crawl.")

# -----------------------------------------------------------------------------
# TAB 2: CHANGE DETECTION AUDIT TRAIL
# -----------------------------------------------------------------------------
with tab_history:
    st.subheader("🚨 Global Change Detection Audit Trail (Requirement 7)")
    st.write("Demonstrates how the crawler captures updates, extensions, and revisions without overwriting historical information:")

    recent_changes = db.get_recent_changes(limit=25)
    if not recent_changes:
        st.info("No changes recorded yet. Click 'Simulate Re-Crawl (Run 2: Change Detection)' in the sidebar to simulate live notification updates!")
    else:
        df_changes = pd.DataFrame(recent_changes)
        display_df = df_changes[["scholarship_name", "field_name", "old_value", "new_value", "detected_at", "evidence"]]
        st.dataframe(display_df, **_fw_df())

# -----------------------------------------------------------------------------
# TAB 3: CRAWL RUNS & ORCHESTRATION
# -----------------------------------------------------------------------------
with tab_runs:
    st.subheader("⚙️ Automated Crawl Cycles Audit")
    st.write("Tracks repeatable multi-run execution history:")
    runs = db.get_recent_crawl_runs(limit=10)
    if runs:
        df_runs = pd.DataFrame(runs)
        st.dataframe(df_runs[["run_number", "started_at", "status", "scholarships_discovered", "scholarships_verified", "scholarships_updated", "scholarships_unchanged", "scholarships_expired", "log_summary"]], **_fw_df())
    else:
        st.info("No crawl runs logged yet.")

# -----------------------------------------------------------------------------
# TAB 4: METHODOLOGY & RUBRIC MAPPING
# -----------------------------------------------------------------------------
with tab_methodology:
    st.subheader("📖 Verification Methodology & Mathematical Scoring Rubric")
    st.markdown("""
    ### Strict Alignment with Assignment Specifications:
    1. **Authenticity Over Quantity**:
       - We evaluate each URL using `SourceClassifier` to distinguish official Government (`.gov.in`, `.nic.in`), University (`.ac.in`), and verified Corporate CSR domains from secondary aggregators.
       - Aggregators (e.g. Buddy4Study, educational blogs) are used strictly for initial discovery and are resolved to official primary sources.
    2. **Anti-Hallucination Framework**:
       - Missing criteria (e.g. Income ceiling, Age limit) default strictly to `Not specified` rather than hallucinated amounts.
       - Every key field links directly to verbatim text extracted from the official source page.
    3. **Deterministic Confidence Score (0 - 100%)**:
       - **Official Domain Authority (35 pts)**: Verifies authoritative domain registration.
       - **Direct DOM Presence (20 pts)**: Matches scheme name and provider in live DOM.
       - **Official Application Channel (15 pts)**: Traceable direct application portal.
       - **Grounded Field Evidence (15 pts)**: Verbatim quotes for benefits & eligibility.
       - **Temporal Currency (15 pts)**: Verified cycle deadline.
       - **Strict Rule**: Only scores **≥ 95.0%** are marked `VERIFIED`. Scores **< 95.0%** are marked `REVIEW_REQUIRED`.
    4. **Change Detection (Zero Overwrite Loss)**:
       - Computes cryptographic SHA-256 fingerprint of core attributes.
       - Logs field alterations with old value, new value, timestamp, and official evidence.
    """)
