"""Overview page — KPIs, top themes, top owner-relevant threads."""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from pt_insights_os.db.duckdb_store import get_connection

st.set_page_config(page_title="Overview | PT Insights OS", page_icon="📊", layout="wide")


@st.cache_data(ttl=300)
def load_data():
    conn = get_connection()
    threads = conn.execute("SELECT * FROM threads").fetchdf()
    posts = conn.execute("SELECT * FROM posts").fetchdf()
    try:
        tags = conn.execute("""
            SELECT ta.post_id, t.l1_domain, t.l2_subdomain, t.l3_tag, ta.confidence
            FROM tag_assignments ta JOIN tags t ON ta.tag_id = t.tag_id
        """).fetchdf()
    except Exception:
        tags = pd.DataFrame()
    try:
        entities = conn.execute("SELECT * FROM entities").fetchdf()
    except Exception:
        entities = pd.DataFrame()
    conn.close()
    return threads, posts, tags, entities


threads, posts, tags, entities = load_data()

# --- Header ---
st.markdown("""
<div style="background: linear-gradient(135deg, #0f3460, #16213e); padding: 1.5rem 2rem;
            border-radius: 14px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0; font-weight:700;">📊 Overview</h2>
    <p style="margin:0.25rem 0 0; opacity:0.8; font-size:0.9rem;">
        High-level view of community activity, themes, and quality metrics
    </p>
</div>
""", unsafe_allow_html=True)

# --- KPI Metrics ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Threads", len(threads))
with col2:
    st.metric("Total Posts", len(posts))
with col3:
    avg_q = threads["thread_quality_score"].mean() if "thread_quality_score" in threads.columns else 0
    st.metric("Avg Thread Quality", f"{avg_q:.2f}" if avg_q else "N/A")
with col4:
    burnout_count = 0
    if "burnout_signal_score" in posts.columns:
        burnout_count = int((posts["burnout_signal_score"] > 0).sum())
    st.metric("Burnout Signals", burnout_count)

st.divider()

# --- Top Themes ---
st.subheader("Top Themes")
if not tags.empty:
    theme_counts = tags.groupby("l1_domain").size().reset_index(name="count").sort_values("count", ascending=False)
    cols = st.columns(min(len(theme_counts), 5))
    for i, (_, row) in enumerate(theme_counts.head(5).iterrows()):
        with cols[i]:
            st.markdown(f"""
            <div style="background:white; border-radius:10px; padding:1rem; text-align:center;
                        box-shadow:0 2px 8px rgba(0,0,0,0.05); border-top:3px solid #0f3460;">
                <div style="font-size:1.5rem; font-weight:700; color:#0f3460;">{row['count']}</div>
                <div style="font-size:0.75rem; color:#888; text-transform:uppercase;">{row['l1_domain']}</div>
            </div>
            """, unsafe_allow_html=True)

    # Bar chart
    st.bar_chart(theme_counts.set_index("l1_domain")["count"])
else:
    st.info("No tags available. Run `make enrich` to generate topic tags.")

st.divider()

# --- Intent Distribution ---
st.subheader("Post Intent Distribution")
if "intent_type" in posts.columns:
    intent_counts = posts["intent_type"].value_counts()
    col1, col2 = st.columns([1, 2])
    with col1:
        for intent, count in intent_counts.items():
            st.markdown(f"**{intent.replace('_', ' ').title()}**: {count}")
    with col2:
        st.bar_chart(intent_counts)
else:
    st.info("Run `make enrich` to classify post intents.")

st.divider()

# --- Top Owner-Relevant Threads ---
st.subheader("Top Owner-Relevant Threads")
if "owner_relevance_score" in threads.columns:
    top = threads.nlargest(5, "owner_relevance_score")
    for _, t in top.iterrows():
        thread_posts = posts[posts["thread_id"] == t["thread_id"]]
        text_col = "text_redacted" if "text_redacted" in thread_posts.columns else "text"
        preview = str(thread_posts.iloc[0][text_col])[:200] if not thread_posts.empty else ""

        with st.container():
            st.markdown(f"""
            <div style="background:white; border-left:4px solid #0f3460; border-radius:8px;
                        padding:1rem; margin:0.5rem 0; box-shadow:0 1px 6px rgba(0,0,0,0.04);">
                <div style="font-weight:600; font-size:0.9rem; color:#1a1a2e;">{preview}...</div>
                <div style="font-size:0.75rem; color:#888; margin-top:0.5rem;">
                    Thread {t['thread_id']} &bull; {int(t.get('post_count', 0) or 0)} posts
                    &bull; Quality: {t.get('thread_quality_score', 0):.2f}
                    &bull; Owner Relevance: {t.get('owner_relevance_score', 0):.2f}
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Run `make enrich` to compute thread scores.")

# --- Entity Summary ---
st.divider()
st.subheader("Entities Mentioned")
if not entities.empty:
    entity_summary = entities.groupby("entity_type").agg(
        count=("entity_id", "size"),
        examples=("entity_value", lambda x: ", ".join(x.unique()[:5]))
    ).reset_index()
    for _, row in entity_summary.iterrows():
        st.markdown(f"**{row['entity_type']}** ({row['count']}): {row['examples']}")
else:
    st.info("No entities extracted yet.")
