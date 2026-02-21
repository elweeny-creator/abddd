"""Thread Deep Dive — full redacted thread with summary, citations, tags, metrics."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from pt_insights_os.db.duckdb_store import get_connection
from pt_insights_os.enrich.summarize import extractive_summary

st.set_page_config(page_title="Thread Deep Dive | PT Insights OS", page_icon="🔍", layout="wide")


@st.cache_data(ttl=300)
def load_data():
    conn = get_connection()
    threads = conn.execute("SELECT * FROM threads").fetchdf()
    posts = conn.execute("SELECT * FROM posts").fetchdf()
    try:
        tags = conn.execute("""
            SELECT ta.post_id, t.l1_domain, t.l2_subdomain, t.l3_tag, ta.confidence, ta.source
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
st.markdown(
    """
<div style="background: linear-gradient(135deg, #0f3460, #16213e); padding: 1.5rem 2rem;
            border-radius: 14px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0; font-weight:700;">🔍 Thread Deep Dive</h2>
    <p style="margin:0.25rem 0 0; opacity:0.8; font-size:0.9rem;">
        Examine a thread with redacted evidence, tags, metrics, and cited summary
    </p>
</div>
""",
    unsafe_allow_html=True,
)

if threads.empty:
    st.warning("No threads available. Run `make ingest` first.")
    st.stop()

# --- Thread Selector ---
text_col = "text_redacted" if "text_redacted" in posts.columns else "text"

# Build thread previews for selector
thread_options = {}
for _, t in threads.iterrows():
    thread_posts = posts[posts["thread_id"] == t["thread_id"]]
    preview = str(thread_posts.iloc[0][text_col])[:80] if not thread_posts.empty else "Empty"
    label = f"{t['thread_id']} — {preview}..."
    thread_options[label] = t["thread_id"]

selected_label = st.selectbox("Select Thread", list(thread_options.keys()))
selected_thread_id = thread_options[selected_label]

# --- Thread Info ---
thread = threads[threads["thread_id"] == selected_thread_id].iloc[0]
thread_posts = posts[posts["thread_id"] == selected_thread_id].sort_values("created_at")

st.divider()

# --- Metrics Row ---
col1, col2, col3, col4, col5, col6 = st.columns(6)

score_cols = [
    ("thread_quality_score", "Quality", col1, "#0f3460"),
    ("novelty_score", "Novelty", col2, "#2d7d2d"),
    ("disagreement_score", "Disagreement", col3, "#ff9800"),
    ("actionable_density", "Actionable", col4, "#7b2d8e"),
    ("owner_relevance_score", "Owner Rel.", col5, "#0f3460"),
    ("burnout_signal_score", "Burnout", col6, "#c62828"),
]

for score_key, label, col, color in score_cols:
    with col:
        val = thread.get(score_key, 0) or 0
        pct = int(float(val) * 100)
        st.markdown(
            f"""
        <div style="background:white; border-radius:10px; padding:0.75rem; text-align:center;
                    box-shadow:0 1px 6px rgba(0,0,0,0.04);">
            <div style="font-size:1.2rem; font-weight:700; color:{color};">{float(val):.2f}</div>
            <div style="font-size:0.7rem; color:#888; text-transform:uppercase;">{label}</div>
            <div style="height:4px; background:#f0f0f0; border-radius:2px; margin-top:0.25rem;">
                <div style="width:{pct}%; height:100%; background:{color}; border-radius:2px;"></div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

st.markdown("")

# --- Tags ---
thread_post_ids = thread_posts["post_id"].tolist()
if not tags.empty:
    thread_tags = tags[tags["post_id"].isin(thread_post_ids)]
    if not thread_tags.empty:
        unique_tags = thread_tags[["l1_domain", "l2_subdomain", "l3_tag"]].drop_duplicates()
        st.markdown("**Tags:**")
        tag_html = ""
        for _, t in unique_tags.iterrows():
            tag_html += (
                f'<span style="display:inline-block; background:#f0f4ff; color:#0f3460; '
                f"padding:0.2rem 0.6rem; border-radius:8px; font-size:0.75rem; margin:0.1rem; "
                f'font-weight:500;">{t["l1_domain"]} > {t["l3_tag"].replace("_", " ")}</span>'
            )
        st.markdown(tag_html, unsafe_allow_html=True)

# --- Entities ---
if not entities.empty:
    thread_entities = entities[entities["post_id"].isin(thread_post_ids)]
    if not thread_entities.empty:
        st.markdown("**Entities:**")
        ent_html = ""
        for _, e in thread_entities.drop_duplicates(
            subset=["entity_type", "entity_value"]
        ).iterrows():
            colors = {
                "INSURER": "#e8f5e8",
                "EMR": "#e8f4fd",
                "CPT_CODE": "#fef3e8",
                "CREDENTIAL": "#f3e8fe",
                "REGULATION": "#fee8e8",
            }
            bg = colors.get(e["entity_type"], "#f0f0f0")
            ent_html += (
                f'<span style="display:inline-block; background:{bg}; padding:0.2rem 0.6rem; '
                f'border-radius:8px; font-size:0.75rem; margin:0.1rem;">'
                f'{e["entity_type"]}: {e["entity_value"]}</span>'
            )
        st.markdown(ent_html, unsafe_allow_html=True)

st.divider()

# --- Evidence-Linked Summary ---
st.markdown("### Evidence Summary")
st.caption("Extractive only — every bullet is a direct quote with source citation")

post_dicts = thread_posts.to_dict("records")
bullets = extractive_summary(post_dicts, max_bullets=5)

if bullets:
    for b in bullets:
        citation = f"thread_id:{b['thread_id']}"
        if b.get("comment_id"):
            citation += f", comment_id:{b['comment_id']}"
        else:
            citation += f", post_id:{b['post_id']}"

        st.markdown(
            f"""
        <div style="background:#fafbfc; border:1px solid #e8e8e8; border-radius:8px;
                    padding:0.75rem 1rem; margin:0.4rem 0; font-size:0.85rem; line-height:1.5;">
            {b['text'].rsplit('[', 1)[0].strip()}
            <span style="color:#0f3460; font-weight:500; font-size:0.75rem;">[{citation}]</span>
        </div>
        """,
            unsafe_allow_html=True,
        )
else:
    st.info("No evidence bullets could be extracted.")

st.divider()

# --- Full Thread ---
st.markdown("### Full Thread (Redacted)")

for _, post in thread_posts.iterrows():
    is_reply = bool(post.get("parent_id"))
    indent = "margin-left: 2rem;" if is_reply else ""
    border_color = "#e0e0e0" if is_reply else "#0f3460"

    created = post.get("created_at", "")
    created_str = str(created)[:19] if created else ""

    intent = post.get("intent_type", "") or ""
    meta_parts = [f"Post {post['post_id']}"]
    if created_str:
        meta_parts.append(created_str)
    if intent and intent != "unknown":
        meta_parts.append(intent)

    with st.expander(
        f"{'↳ ' if is_reply else ''}{str(post[text_col])[:100]}...", expanded=not is_reply
    ):
        st.markdown(
            f"""
        <div style="{indent} background:white; border-left:3px solid {border_color};
                    border-radius:8px; padding:1rem;">
            <div style="font-size:0.85rem; line-height:1.6;">{post[text_col]}</div>
            <div style="font-size:0.7rem; color:#888; margin-top:0.5rem;">
                {' &bull; '.join(meta_parts)}
                &bull; Reactions: {int(post.get('reactions', 0) or 0)}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
