"""Owner's Briefing — generate markdown briefing from filtered slice with citations."""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from pt_insights_os.db.duckdb_store import get_connection
from pt_insights_os.enrich.summarize import extractive_summary, format_briefing, validate_citations

st.set_page_config(page_title="Owner's Briefing | PT Insights OS", page_icon="📋", layout="wide")


@st.cache_data(ttl=300)
def load_data():
    conn = get_connection()
    posts = conn.execute("SELECT * FROM posts").fetchdf()
    threads = conn.execute("SELECT * FROM threads").fetchdf()
    try:
        tags = conn.execute("""
            SELECT ta.post_id, t.l1_domain, t.l2_subdomain, t.l3_tag
            FROM tag_assignments ta JOIN tags t ON ta.tag_id = t.tag_id
        """).fetchdf()
    except Exception:
        tags = pd.DataFrame()
    conn.close()
    return posts, threads, tags


posts, threads, tags = load_data()

# --- Header ---
st.markdown("""
<div style="background: linear-gradient(135deg, #0f3460, #16213e); padding: 1.5rem 2rem;
            border-radius: 14px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0; font-weight:700;">📋 Owner's Briefing</h2>
    <p style="margin:0.25rem 0 0; opacity:0.8; font-size:0.9rem;">
        Generate a markdown briefing from a filtered slice — every bullet cites source records
    </p>
</div>
""", unsafe_allow_html=True)

# --- Filter Controls ---
st.markdown("### Configure Briefing")

col1, col2, col3 = st.columns(3)

with col1:
    briefing_title = st.text_input("Briefing Title", value="PT Practice Owner Intelligence Brief")

with col2:
    # Topic filter
    if not tags.empty:
        domains = ["All"] + sorted(tags["l1_domain"].unique())
        selected_domain = st.selectbox("Topic Domain", domains)
    else:
        selected_domain = "All"

with col3:
    max_bullets = st.slider("Max Evidence Bullets", 3, 10, 5)

# Additional filters
fcol1, fcol2, fcol3 = st.columns(3)

with fcol1:
    if "intent_type" in posts.columns:
        intents = ["All"] + sorted([s for s in posts["intent_type"].unique() if s and s != "unknown"])
        filter_intent = st.selectbox("Intent Type", intents)
    else:
        filter_intent = "All"

with fcol2:
    if "setting_type" in posts.columns:
        settings = ["All"] + sorted([s for s in posts["setting_type"].unique() if s and s != "unknown"])
        filter_setting = st.selectbox("Setting Type", settings)
    else:
        filter_setting = "All"

with fcol3:
    if "business_stage" in posts.columns:
        stages = ["All"] + sorted([s for s in posts["business_stage"].unique() if s and s != "unknown"])
        filter_stage = st.selectbox("Business Stage", stages)
    else:
        filter_stage = "All"

# Quick topic chips
st.markdown("**Quick Topics:**")
qcol = st.columns(6)
quick_topics = [
    ("Practice Ownership", "Scaling & Growth"),
    ("Staffing", "Staffing"),
    ("Reimbursement", "Reimbursement"),
    ("Marketing", "Sales & Marketing"),
    ("Burnout", "Burnout & Wellness"),
    ("Legal", "Legal & Compliance"),
]

for i, (label, domain) in enumerate(quick_topics):
    with qcol[i]:
        if st.button(label, key=f"qt_{label}", use_container_width=True):
            st.session_state["quick_domain"] = domain

# Apply quick topic if set
if "quick_domain" in st.session_state:
    selected_domain = st.session_state.pop("quick_domain")

st.divider()

# --- Generate Briefing ---
if st.button("Generate Briefing", type="primary", use_container_width=True):
    # Filter posts
    filtered_posts = posts.copy()

    if selected_domain != "All" and not tags.empty:
        matching_post_ids = tags[tags["l1_domain"] == selected_domain]["post_id"].unique()
        filtered_posts = filtered_posts[filtered_posts["post_id"].isin(matching_post_ids)]

    if filter_intent != "All" and "intent_type" in filtered_posts.columns:
        filtered_posts = filtered_posts[filtered_posts["intent_type"] == filter_intent]

    if filter_setting != "All" and "setting_type" in filtered_posts.columns:
        filtered_posts = filtered_posts[filtered_posts["setting_type"] == filter_setting]

    if filter_stage != "All" and "business_stage" in filtered_posts.columns:
        filtered_posts = filtered_posts[filtered_posts["business_stage"] == filter_stage]

    if filtered_posts.empty:
        st.warning("No posts match the current filters. Try broadening your selection.")
    else:
        post_dicts = filtered_posts.to_dict("records")
        bullets = extractive_summary(post_dicts, max_bullets=max_bullets)

        if not bullets:
            st.warning("Could not extract evidence bullets from the filtered posts.")
        else:
            briefing = format_briefing(briefing_title, bullets)

            # Validate citations
            is_valid = validate_citations(briefing)

            if not is_valid:
                st.error("CITATION GUARD: Some bullets are missing source IDs. This briefing cannot be generated.")
            else:
                # Show success
                st.success(f"Briefing generated with {len(bullets)} evidence bullets. All citations verified.")

                # Display the briefing
                st.markdown("---")
                st.markdown("### Generated Briefing")

                # Styled briefing
                st.markdown(f"""
                <div style="background:white; border-radius:12px; padding:2rem;
                            box-shadow:0 2px 12px rgba(0,0,0,0.06); border:1px solid #eee;">
                    <h2 style="color:#0f3460; margin-top:0;">{briefing_title}</h2>
                    <p style="font-size:0.8rem; color:#888;">
                        Generated from {len(filtered_posts)} posts
                        {f' in {selected_domain}' if selected_domain != 'All' else ''}
                        | All bullets cite source records
                    </p>
                    <hr style="border:none; border-top:1px solid #eee; margin:1rem 0;">
                """, unsafe_allow_html=True)

                for b in bullets:
                    citation = f"thread_id:{b['thread_id']}"
                    if b.get("comment_id"):
                        citation += f", comment_id:{b['comment_id']}"
                    else:
                        citation += f", post_id:{b['post_id']}"

                    sentence = b["text"].rsplit("[", 1)[0].strip()

                    st.markdown(f"""
                    <div style="background:#fafbfc; border:1px solid #e8e8e8; border-radius:8px;
                                padding:0.75rem 1rem; margin:0.4rem 0; font-size:0.85rem; line-height:1.5;">
                        <span style="color:#333;">• {sentence}</span>
                        <span style="color:#0f3460; font-weight:600; font-size:0.75rem;">[{citation}]</span>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

                # Download options
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        "Download as Markdown",
                        briefing,
                        file_name=f"{briefing_title.lower().replace(' ', '_')}.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )
                with col2:
                    st.download_button(
                        "Download Raw Bullets (CSV)",
                        pd.DataFrame(bullets).to_csv(index=False),
                        file_name="briefing_bullets.csv",
                        mime="text/csv",
                        use_container_width=True,
                    )
else:
    st.markdown("""
    <div style="text-align:center; padding:2rem; color:#888;">
        <div style="font-size:2rem; margin-bottom:0.5rem;">📋</div>
        <p>Configure filters above and click <b>Generate Briefing</b>.</p>
        <p style="font-size:0.8rem;">Every bullet will cite its source thread and post IDs.</p>
    </div>
    """, unsafe_allow_html=True)
