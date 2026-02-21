"""Topic Explorer — taxonomy tree with faceted filters."""

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from pt_insights_os.db.duckdb_store import get_connection
from pt_insights_os.taxonomy.tagger import load_taxonomy

st.set_page_config(page_title="Topic Explorer | PT Insights OS", page_icon="🏷️", layout="wide")


@st.cache_data(ttl=300)
def load_data():
    conn = get_connection()
    posts = conn.execute("SELECT * FROM posts").fetchdf()
    try:
        tags = conn.execute("""
            SELECT ta.post_id, ta.confidence, ta.source,
                   t.l1_domain, t.l2_subdomain, t.l3_tag
            FROM tag_assignments ta JOIN tags t ON ta.tag_id = t.tag_id
        """).fetchdf()
    except Exception:
        tags = pd.DataFrame()
    conn.close()
    return posts, tags


posts, tags = load_data()

# --- Header ---
st.markdown("""
<div style="background: linear-gradient(135deg, #0f3460, #16213e); padding: 1.5rem 2rem;
            border-radius: 14px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0; font-weight:700;">🏷️ Topic Explorer</h2>
    <p style="margin:0.25rem 0 0; opacity:0.8; font-size:0.9rem;">
        Browse the PT taxonomy tree with faceted filters
    </p>
</div>
""", unsafe_allow_html=True)

if tags.empty:
    st.warning("No tags available. Run `make enrich` to generate topic tags.")
    st.stop()

# --- Sidebar Filters ---
st.sidebar.markdown("### Filters")

# L1 Domain filter
domains = sorted(tags["l1_domain"].unique())
selected_domain = st.sidebar.selectbox("Domain (L1)", ["All"] + domains)

# L2 Subdomain filter
if selected_domain != "All":
    subdomains = sorted(tags[tags["l1_domain"] == selected_domain]["l2_subdomain"].unique())
else:
    subdomains = sorted(tags["l2_subdomain"].unique())
selected_subdomain = st.sidebar.selectbox("Subdomain (L2)", ["All"] + list(subdomains))

# Score filters
if "setting_type" in posts.columns:
    settings = ["All"] + sorted([s for s in posts["setting_type"].unique() if s and s != "unknown"])
    selected_setting = st.sidebar.selectbox("Setting Type", settings)
else:
    selected_setting = "All"

if "business_stage" in posts.columns:
    stages = ["All"] + sorted([s for s in posts["business_stage"].unique() if s and s != "unknown"])
    selected_stage = st.sidebar.selectbox("Business Stage", stages)
else:
    selected_stage = "All"

if "intent_type" in posts.columns:
    intents = ["All"] + sorted([s for s in posts["intent_type"].unique() if s])
    selected_intent = st.sidebar.selectbox("Intent Type", intents)
else:
    selected_intent = "All"

min_confidence = st.sidebar.slider("Min Tag Confidence", 0.0, 1.0, 0.0, 0.05)

# --- Apply Filters ---
filtered_tags = tags.copy()
if selected_domain != "All":
    filtered_tags = filtered_tags[filtered_tags["l1_domain"] == selected_domain]
if selected_subdomain != "All":
    filtered_tags = filtered_tags[filtered_tags["l2_subdomain"] == selected_subdomain]
filtered_tags = filtered_tags[filtered_tags["confidence"] >= min_confidence]

# Filter posts
filtered_post_ids = set(filtered_tags["post_id"].unique())
filtered_posts = posts[posts["post_id"].isin(filtered_post_ids)]

if selected_setting != "All" and "setting_type" in filtered_posts.columns:
    filtered_posts = filtered_posts[filtered_posts["setting_type"] == selected_setting]
if selected_stage != "All" and "business_stage" in filtered_posts.columns:
    filtered_posts = filtered_posts[filtered_posts["business_stage"] == selected_stage]
if selected_intent != "All" and "intent_type" in filtered_posts.columns:
    filtered_posts = filtered_posts[filtered_posts["intent_type"] == selected_intent]

# --- Taxonomy Tree ---
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### Taxonomy Tree")
    taxonomy = load_taxonomy()
    for domain_id, domain in taxonomy["domains"].items():
        domain_count = len(filtered_tags[filtered_tags["l1_domain"] == domain["label"]])
        if domain_count > 0 or selected_domain == "All":
            with st.expander(f"**{domain['label']}** ({domain_count})", expanded=(selected_domain == domain["label"])):
                for sub_id, sub in domain["subdomains"].items():
                    sub_count = len(filtered_tags[filtered_tags["l2_subdomain"] == sub["label"]])
                    if sub_count > 0:
                        st.markdown(f"&nbsp;&nbsp;📂 **{sub['label']}** ({sub_count})")
                        for tag in sub["tags"]:
                            tag_count = len(filtered_tags[filtered_tags["l3_tag"] == tag])
                            if tag_count > 0:
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;🏷️ {tag.replace('_', ' ')} ({tag_count})")

with col2:
    st.markdown(f"### Matching Posts ({len(filtered_posts)})")

    if filtered_posts.empty:
        st.info("No posts match the current filters.")
    else:
        text_col = "text_redacted" if "text_redacted" in filtered_posts.columns else "text"
        for _, post in filtered_posts.head(7).iterrows():
            # Get tags for this post
            post_tags = filtered_tags[filtered_tags["post_id"] == post["post_id"]]
            tag_html = " ".join(
                f'<span style="background:#f0f4ff; color:#0f3460; padding:0.1rem 0.4rem; '
                f'border-radius:6px; font-size:0.7rem; margin:0.1rem;">{t.replace("_", " ")}</span>'
                for t in post_tags["l3_tag"].unique()[:5]
            )

            intent = post.get("intent_type", "") or ""
            stage = post.get("business_stage", "") or ""
            setting = post.get("setting_type", "") or ""
            meta_parts = [p for p in [intent, stage, setting] if p and p != "unknown"]
            meta_str = " &bull; ".join(meta_parts)

            st.markdown(f"""
            <div style="background:white; border-radius:10px; padding:1rem; margin:0.5rem 0;
                        box-shadow:0 1px 6px rgba(0,0,0,0.04); border-left:3px solid #0f3460;">
                <div style="font-size:0.85rem; line-height:1.5;">{str(post[text_col])[:300]}...</div>
                <div style="margin-top:0.5rem;">{tag_html}</div>
                <div style="font-size:0.7rem; color:#888; margin-top:0.25rem;">
                    Post {post['post_id']} &bull; Thread {post.get('thread_id', '')}
                    {' &bull; ' + meta_str if meta_str else ''}
                </div>
            </div>
            """, unsafe_allow_html=True)

        if len(filtered_posts) > 7:
            st.caption(f"Showing 7 of {len(filtered_posts)} matching posts")
