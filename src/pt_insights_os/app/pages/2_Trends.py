"""Trends page — topics over time, emerging topics, disagreement hotspots."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from pt_insights_os.db.duckdb_store import get_connection

st.set_page_config(page_title="Trends | PT Insights OS", page_icon="📈", layout="wide")


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
    conn.close()
    return threads, posts, tags


threads, posts, tags = load_data()

# --- Header ---
st.markdown(
    """
<div style="background: linear-gradient(135deg, #0f3460, #16213e); padding: 1.5rem 2rem;
            border-radius: 14px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0; font-weight:700;">📈 Trends</h2>
    <p style="margin:0.25rem 0 0; opacity:0.8; font-size:0.9rem;">
        Topic evolution, emerging discussions, and disagreement hotspots
    </p>
</div>
""",
    unsafe_allow_html=True,
)

# --- Topics Over Time ---
st.subheader("Topics Over Time")

if not tags.empty and "created_at" in posts.columns:
    # Merge tags with post timestamps
    tag_time = tags.merge(posts[["post_id", "created_at"]], on="post_id", how="left")
    tag_time["created_at"] = pd.to_datetime(tag_time["created_at"], errors="coerce")
    tag_time = tag_time.dropna(subset=["created_at"])

    if not tag_time.empty:
        tag_time["month"] = tag_time["created_at"].dt.to_period("M").astype(str)
        topic_time = tag_time.groupby(["month", "l1_domain"]).size().reset_index(name="count")
        pivot = topic_time.pivot(index="month", columns="l1_domain", values="count").fillna(0)
        st.line_chart(pivot)
    else:
        st.info("No timestamped tag data available.")
else:
    st.info("Run `make enrich` to generate topic trends.")

st.divider()

# --- Emerging Topics ---
st.subheader("Emerging Topics")
st.caption("Tags that appear in recent threads but not earlier ones")

if not tags.empty and "created_at" in posts.columns:
    tag_time = tags.merge(posts[["post_id", "created_at"]], on="post_id", how="left")
    tag_time["created_at"] = pd.to_datetime(tag_time["created_at"], errors="coerce")
    tag_time = tag_time.dropna(subset=["created_at"])

    if not tag_time.empty:
        median_date = tag_time["created_at"].median()
        recent = tag_time[tag_time["created_at"] >= median_date]
        older = tag_time[tag_time["created_at"] < median_date]

        recent_tags = set(recent["l3_tag"].unique())
        older_tags = set(older["l3_tag"].unique())
        emerging = recent_tags - older_tags

        if emerging:
            cols = st.columns(min(len(emerging), 5))
            for i, tag in enumerate(list(emerging)[:5]):
                with cols[i]:
                    count = len(recent[recent["l3_tag"] == tag])
                    st.markdown(
                        f"""
                    <div style="background:#e8f5e8; border-radius:10px; padding:0.75rem;
                                text-align:center; border:1px solid #c8e6c9;">
                        <div style="font-weight:600; color:#2d7d2d;">{tag.replace('_', ' ')}</div>
                        <div style="font-size:0.75rem; color:#666;">{count} mentions</div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )
        else:
            st.info("No emerging topics detected — all topics appear consistently.")
    else:
        st.info("Insufficient timestamped data for trend analysis.")
else:
    st.info("Run `make enrich` first.")

st.divider()

# --- Disagreement Hotspots ---
st.subheader("Disagreement Hotspots")
st.caption("Threads with highest disagreement scores — where opinions diverge")

if "disagreement_score" in threads.columns:
    hotspots = threads.nlargest(5, "disagreement_score")
    text_col = "text_redacted" if "text_redacted" in posts.columns else "text"

    for _, t in hotspots.iterrows():
        thread_posts = posts[posts["thread_id"] == t["thread_id"]]
        preview = str(thread_posts.iloc[0][text_col])[:200] if not thread_posts.empty else ""
        disagree = t.get("disagreement_score", 0) or 0
        disagree_pct = int(disagree * 100)

        st.markdown(
            f"""
        <div style="background:white; border-left:4px solid #ff9800; border-radius:8px;
                    padding:1rem; margin:0.5rem 0; box-shadow:0 1px 6px rgba(0,0,0,0.04);">
            <div style="font-weight:600; font-size:0.9rem;">{preview}...</div>
            <div style="font-size:0.75rem; color:#888; margin-top:0.5rem;">
                Thread {t['thread_id']} &bull; Disagreement: {disagree:.2f}
                &bull; {int(t.get('post_count', 0) or 0)} posts
            </div>
            <div style="height:6px; background:#f0f0f0; border-radius:3px; margin-top:0.5rem;">
                <div style="width:{disagree_pct}%; height:100%; background:linear-gradient(90deg, #ff9800, #f44336);
                            border-radius:3px;"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
else:
    st.info("Run `make enrich` to compute disagreement scores.")

st.divider()

# --- Burnout Trend ---
st.subheader("Burnout Signal Density")
if "burnout_signal_score" in posts.columns:
    burnout_posts = posts[posts["burnout_signal_score"] > 0]
    st.metric("Posts with Burnout Signals", len(burnout_posts))

    if not burnout_posts.empty:
        text_col = "text_redacted" if "text_redacted" in burnout_posts.columns else "text"
        st.markdown("**Sample burnout-signal posts:**")
        for _, post in burnout_posts.head(3).iterrows():
            st.markdown(
                f"""
            <div style="background:#fff3f3; border-radius:8px; padding:0.75rem; margin:0.25rem 0;
                        border-left:3px solid #c62828;">
                <div style="font-size:0.85rem;">{str(post[text_col])[:250]}...</div>
                <div style="font-size:0.7rem; color:#888; margin-top:0.25rem;">
                    Post {post['post_id']}
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )
