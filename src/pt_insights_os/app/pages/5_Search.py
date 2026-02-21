"""Search page — keyword + semantic search with evidence and filters."""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from pt_insights_os.db.duckdb_store import get_connection
from pt_insights_os.search.index import VectorIndex
from pt_insights_os.search.retrieve import hybrid_search, keyword_search, format_search_result

st.set_page_config(page_title="Search | PT Insights OS", page_icon="🔎", layout="wide")


@st.cache_data(ttl=300)
def load_posts():
    conn = get_connection()
    posts = conn.execute("SELECT * FROM posts").fetchdf()
    try:
        tags = conn.execute("""
            SELECT ta.post_id, t.l1_domain, t.l3_tag
            FROM tag_assignments ta JOIN tags t ON ta.tag_id = t.tag_id
        """).fetchdf()
    except Exception:
        tags = pd.DataFrame()
    conn.close()
    return posts, tags


@st.cache_resource
def load_index():
    idx = VectorIndex()
    if idx.load():
        return idx
    return None


posts, tags = load_posts()
index = load_index()

# --- Header ---
st.markdown("""
<div style="background: linear-gradient(135deg, #0f3460, #16213e); padding: 1.5rem 2rem;
            border-radius: 14px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0; font-weight:700;">🔎 Search</h2>
    <p style="margin:0.25rem 0 0; opacity:0.8; font-size:0.9rem;">
        Keyword + semantic search — every result traces to source records
    </p>
</div>
""", unsafe_allow_html=True)

# --- Search Input ---
col1, col2 = st.columns([3, 1])
with col1:
    query = st.text_input("Search query", placeholder="e.g., cash-based transition, burnout, hiring...")
with col2:
    search_mode = st.selectbox("Mode", ["Hybrid", "Keyword Only", "Semantic Only"])

# --- Filters ---
with st.expander("Advanced Filters", expanded=False):
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        if "intent_type" in posts.columns:
            intents = ["All"] + sorted([s for s in posts["intent_type"].unique() if s and s != "unknown"])
            filter_intent = st.selectbox("Intent", intents, key="search_intent")
        else:
            filter_intent = "All"
    with fcol2:
        if "setting_type" in posts.columns:
            settings = ["All"] + sorted([s for s in posts["setting_type"].unique() if s and s != "unknown"])
            filter_setting = st.selectbox("Setting", settings, key="search_setting")
        else:
            filter_setting = "All"
    with fcol3:
        max_results = st.slider("Max Results", 3, 20, 7, key="search_max")

# --- Quick Filter Chips ---
st.markdown("""
<div style="margin: 0.5rem 0 1rem;">
    <span style="display:inline-block; padding:0.3rem 0.7rem; border-radius:16px; font-size:0.75rem;
                 font-weight:500; margin:0.15rem; background:#e8f4fd; color:#0f3460; border:1px solid #0f3460;
                 cursor:pointer;">Ownership</span>
    <span style="display:inline-block; padding:0.3rem 0.7rem; border-radius:16px; font-size:0.75rem;
                 font-weight:500; margin:0.15rem; background:#fef3e8; color:#c66b00; border:1px solid #c66b00;">Staffing</span>
    <span style="display:inline-block; padding:0.3rem 0.7rem; border-radius:16px; font-size:0.75rem;
                 font-weight:500; margin:0.15rem; background:#e8f5e8; color:#2d7d2d; border:1px solid #2d7d2d;">Reimbursement</span>
    <span style="display:inline-block; padding:0.3rem 0.7rem; border-radius:16px; font-size:0.75rem;
                 font-weight:500; margin:0.15rem; background:#f3e8fe; color:#7b2d8e; border:1px solid #7b2d8e;">Marketing</span>
    <span style="display:inline-block; padding:0.3rem 0.7rem; border-radius:16px; font-size:0.75rem;
                 font-weight:500; margin:0.15rem; background:#fee8e8; color:#c62828; border:1px solid #c62828;">Burnout</span>
    <span style="display:inline-block; padding:0.3rem 0.7rem; border-radius:16px; font-size:0.75rem;
                 font-weight:500; margin:0.15rem; background:#e8eefe; color:#3949ab; border:1px solid #3949ab;">Legal</span>
</div>
""", unsafe_allow_html=True)

# --- Search Execution ---
if query:
    with st.spinner("Searching..."):
        filtered_posts = posts.copy()
        if filter_intent != "All" and "intent_type" in filtered_posts.columns:
            filtered_posts = filtered_posts[filtered_posts["intent_type"] == filter_intent]
        if filter_setting != "All" and "setting_type" in filtered_posts.columns:
            filtered_posts = filtered_posts[filtered_posts["setting_type"] == filter_setting]

        if search_mode == "Keyword Only" or index is None:
            results = keyword_search(query, filtered_posts, top_k=max_results)
        elif search_mode == "Semantic Only" and index is not None:
            results = index.search(query, top_k=max_results)
        else:
            results = hybrid_search(query, filtered_posts, index, top_k=max_results)

    st.markdown(f"**{len(results)} results found**")
    st.divider()

    text_col = "text_redacted" if "text_redacted" in posts.columns else "text"

    for i, result in enumerate(results):
        post_id = result.get("post_id", "")
        thread_id = result.get("thread_id", "")
        score = result.get("final_score", result.get("score", 0))
        text = result.get("text", "")

        # If text is from chunk, try to get full post text
        if not text and post_id:
            match = posts[posts["post_id"] == post_id]
            if not match.empty:
                text = str(match.iloc[0][text_col])

        excerpt = text[:400] + "..." if len(text) > 400 else text

        # Get tags
        result_tags = []
        if not tags.empty and post_id:
            result_tags = tags[tags["post_id"] == post_id]["l3_tag"].unique()[:5]

        tag_html = " ".join(
            f'<span style="background:#f0f4ff; color:#0f3460; padding:0.1rem 0.4rem; '
            f'border-radius:6px; font-size:0.65rem; margin:0.05rem;">{t.replace("_", " ")}</span>'
            for t in result_tags
        )

        sources = result.get("sources", [result.get("source", "unknown")])
        source_str = " + ".join(sources) if isinstance(sources, list) else str(sources)

        # Score bar
        score_pct = int(min(1, max(0, score)) * 100)

        st.markdown(f"""
        <div style="background:white; border-radius:10px; padding:1.25rem; margin:0.5rem 0;
                    box-shadow:0 2px 8px rgba(0,0,0,0.05); border-left:4px solid #0f3460;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                <div style="font-size:0.7rem; color:#888;">
                    Post {post_id} &bull; Thread {thread_id} &bull; {source_str}
                </div>
                <div style="font-size:0.75rem; font-weight:600; color:#0f3460;">
                    Score: {score:.3f}
                </div>
            </div>
            <div style="font-size:0.85rem; line-height:1.5; margin-bottom:0.5rem;">{excerpt}</div>
            <div>{tag_html}</div>
            <div style="height:4px; background:#f0f0f0; border-radius:2px; margin-top:0.5rem;">
                <div style="width:{score_pct}%; height:100%; background:linear-gradient(90deg, #0f3460, #3f72af);
                            border-radius:2px;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div style="text-align:center; padding:3rem; color:#888;">
        <div style="font-size:2rem; margin-bottom:0.5rem;">🔎</div>
        <p>Enter a search query above to find relevant discussions.</p>
        <p style="font-size:0.8rem;">Try: "cash-based transition", "burnout documentation", "hiring salary"</p>
    </div>
    """, unsafe_allow_html=True)
