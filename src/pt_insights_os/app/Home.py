"""PT Insights OS — Home / Landing Page."""

import streamlit as st
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

st.set_page_config(
    page_title="PT Insights OS",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Global CSS for a polished, ADHD-friendly UI ---
st.markdown("""
<style>
    /* Import clean font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styling */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #e8e8e8;
    }

    /* Main header styling */
    .main-header {
        background: linear-gradient(135deg, #0f3460 0%, #16213e 50%, #1a1a2e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        color: white;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    }
    .main-header h1 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0 0 0.5rem 0;
        letter-spacing: -0.02em;
    }
    .main-header p {
        font-size: 1rem;
        opacity: 0.85;
        margin: 0;
        font-weight: 300;
    }

    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        border: 1px solid #f0f0f0;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
    }
    .kpi-number {
        font-size: 2rem;
        font-weight: 700;
        color: #0f3460;
        line-height: 1;
        margin-bottom: 0.25rem;
    }
    .kpi-label {
        font-size: 0.8rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 500;
    }

    /* Nav cards */
    .nav-card {
        background: white;
        border-radius: 14px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
        border: 1px solid #eee;
        transition: all 0.25s ease;
        cursor: pointer;
        height: 100%;
    }
    .nav-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
        border-color: #0f3460;
    }
    .nav-card .icon {
        font-size: 1.8rem;
        margin-bottom: 0.75rem;
    }
    .nav-card h3 {
        font-size: 1rem;
        font-weight: 600;
        margin: 0 0 0.5rem 0;
        color: #1a1a2e;
    }
    .nav-card p {
        font-size: 0.85rem;
        color: #666;
        margin: 0;
        line-height: 1.4;
    }

    /* Quick filter chips */
    .chip {
        display: inline-block;
        padding: 0.4rem 0.9rem;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 500;
        margin: 0.25rem;
        cursor: pointer;
        transition: all 0.2s;
        border: 1.5px solid;
    }
    .chip-ownership { background: #e8f4fd; color: #0f3460; border-color: #0f3460; }
    .chip-staffing { background: #fef3e8; color: #c66b00; border-color: #c66b00; }
    .chip-reimbursement { background: #e8f5e8; color: #2d7d2d; border-color: #2d7d2d; }
    .chip-marketing { background: #f3e8fe; color: #7b2d8e; border-color: #7b2d8e; }
    .chip-burnout { background: #fee8e8; color: #c62828; border-color: #c62828; }
    .chip-legal { background: #e8eefe; color: #3949ab; border-color: #3949ab; }

    /* Section headers */
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a2e;
        margin: 1.5rem 0 0.75rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #f0f0f0;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Streamlit containers */
    .stMetric {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* Thread cards */
    .thread-card {
        background: white;
        border-radius: 12px;
        padding: 1.25rem;
        margin: 0.5rem 0;
        box-shadow: 0 1px 6px rgba(0,0,0,0.05);
        border-left: 4px solid #0f3460;
        transition: all 0.2s;
    }
    .thread-card:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    }
    .thread-card .title {
        font-weight: 600;
        font-size: 0.95rem;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .thread-card .meta {
        font-size: 0.8rem;
        color: #888;
    }
    .thread-card .tags {
        margin-top: 0.5rem;
    }
    .tag-badge {
        display: inline-block;
        background: #f0f4ff;
        color: #0f3460;
        padding: 0.15rem 0.5rem;
        border-radius: 8px;
        font-size: 0.7rem;
        font-weight: 500;
        margin: 0.1rem;
    }

    /* Evidence box */
    .evidence-box {
        background: #fafbfc;
        border: 1px solid #e8e8e8;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        font-size: 0.85rem;
        line-height: 1.5;
    }
    .evidence-citation {
        color: #0f3460;
        font-weight: 500;
        font-size: 0.75rem;
    }

    /* Score bars */
    .score-bar {
        height: 6px;
        border-radius: 3px;
        background: #f0f0f0;
        overflow: hidden;
        margin-top: 0.25rem;
    }
    .score-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 0.3s;
    }
    .score-fill-blue { background: linear-gradient(90deg, #0f3460, #3f72af); }
    .score-fill-green { background: linear-gradient(90deg, #2d7d2d, #4caf50); }
    .score-fill-orange { background: linear-gradient(90deg, #c66b00, #ff9800); }
    .score-fill-red { background: linear-gradient(90deg, #c62828, #ef5350); }
</style>
""", unsafe_allow_html=True)


def load_data():
    """Load data from DuckDB."""
    from pt_insights_os.db.duckdb_store import get_connection
    conn = get_connection()
    try:
        threads = conn.execute("SELECT * FROM threads").fetchdf()
        posts = conn.execute("SELECT * FROM posts").fetchdf()
        try:
            tags = conn.execute("""
                SELECT ta.post_id, t.l1_domain, t.l2_subdomain, t.l3_tag, ta.confidence, ta.source
                FROM tag_assignments ta JOIN tags t ON ta.tag_id = t.tag_id
            """).fetchdf()
        except Exception:
            tags = None
        try:
            entities = conn.execute("SELECT * FROM entities").fetchdf()
        except Exception:
            entities = None
    finally:
        conn.close()
    return threads, posts, tags, entities


def main():
    threads, posts, tags, entities = load_data()

    # --- Header ---
    st.markdown("""
    <div class="main-header">
        <h1>PT Insights OS</h1>
        <p>Community intelligence for the Uncaged Clinician — powered by real conversations, zero hallucination</p>
    </div>
    """, unsafe_allow_html=True)

    # --- KPI Row ---
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">{len(threads)}</div>
            <div class="kpi-label">Threads</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">{len(posts)}</div>
            <div class="kpi-label">Posts</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        unique_tags = tags["l1_domain"].nunique() if tags is not None and not tags.empty else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">{unique_tags}</div>
            <div class="kpi-label">Topic Domains</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        entity_count = len(entities) if entities is not None else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">{entity_count}</div>
            <div class="kpi-label">Entities Found</div>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        avg_quality = threads["thread_quality_score"].mean() if "thread_quality_score" in threads.columns else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-number">{avg_quality:.2f}</div>
            <div class="kpi-label">Avg Quality</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # --- Quick Filters ---
    st.markdown('<div class="section-header">Quick Filters</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="margin-bottom: 1rem;">
        <span class="chip chip-ownership">Ownership</span>
        <span class="chip chip-staffing">Staffing</span>
        <span class="chip chip-reimbursement">Reimbursement</span>
        <span class="chip chip-marketing">Marketing</span>
        <span class="chip chip-burnout">Burnout</span>
        <span class="chip chip-legal">Legal</span>
    </div>
    """, unsafe_allow_html=True)

    # --- Top Themes ---
    if tags is not None and not tags.empty:
        st.markdown('<div class="section-header">Top Themes</div>', unsafe_allow_html=True)
        theme_counts = tags.groupby("l1_domain").size().sort_values(ascending=False).head(7)
        cols = st.columns(min(len(theme_counts), 7))
        for i, (theme, count) in enumerate(theme_counts.items()):
            with cols[i % len(cols)]:
                st.markdown(f"""
                <div class="kpi-card" style="border-left: 3px solid #0f3460;">
                    <div class="kpi-number" style="font-size: 1.4rem;">{count}</div>
                    <div class="kpi-label">{theme}</div>
                </div>
                """, unsafe_allow_html=True)

    # --- Top Owner-Relevant Threads ---
    st.markdown('<div class="section-header">Top Owner-Relevant Threads</div>', unsafe_allow_html=True)
    if "owner_relevance_score" in threads.columns:
        top_threads = threads.nlargest(5, "owner_relevance_score")
    else:
        top_threads = threads.head(5)

    for _, thread in top_threads.iterrows():
        # Get first post text for this thread
        thread_posts = posts[posts["thread_id"] == thread["thread_id"]]
        first_text = ""
        if not thread_posts.empty:
            text_col = "text_redacted" if "text_redacted" in thread_posts.columns else "text"
            first_text = str(thread_posts.iloc[0][text_col])[:200]

        # Get tags for this thread
        thread_tags = []
        if tags is not None and not tags.empty:
            thread_post_ids = thread_posts["post_id"].tolist()
            thread_tag_df = tags[tags["post_id"].isin(thread_post_ids)]
            thread_tags = thread_tag_df["l3_tag"].unique()[:5]

        tag_html = " ".join(f'<span class="tag-badge">{t.replace("_", " ")}</span>' for t in thread_tags)

        quality = thread.get("thread_quality_score", 0) or 0
        quality_pct = int(quality * 100)

        st.markdown(f"""
        <div class="thread-card">
            <div class="title">{first_text}...</div>
            <div class="meta">
                Thread {thread['thread_id']}
                &bull; {int(thread.get('post_count', 0) or 0)} posts
                &bull; {int(thread.get('total_reactions', 0) or 0)} reactions
                &bull; Quality: {quality:.2f}
            </div>
            <div class="tags">{tag_html}</div>
            <div class="score-bar"><div class="score-fill score-fill-blue" style="width: {quality_pct}%"></div></div>
        </div>
        """, unsafe_allow_html=True)

    # --- Navigation Cards ---
    st.markdown('<div class="section-header">Continue Exploring</div>', unsafe_allow_html=True)

    nav_items = [
        ("📊", "Overview", "KPIs, top themes, and high-signal threads"),
        ("📈", "Trends", "Topics over time, emerging discussions, hotspots"),
        ("🏷️", "Topic Explorer", "Browse the full taxonomy with filters"),
        ("🔍", "Thread Deep Dive", "Examine threads with evidence and citations"),
        ("🔎", "Search", "Keyword + semantic search with evidence"),
        ("📁", "Collections", "Save and organize threads for later"),
        ("📋", "Owner's Briefing", "Generate markdown briefings with citations"),
    ]

    cols = st.columns(4)
    for i, (icon, title, desc) in enumerate(nav_items):
        with cols[i % 4]:
            st.markdown(f"""
            <div class="nav-card">
                <div class="icon">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    # --- Footer ---
    st.markdown("---")
    st.caption("PT Insights OS | All insights trace to source records | Privacy-first: no raw PII exposed")


if __name__ == "__main__":
    main()
else:
    main()
