"""Collections — save threads into named collections, add notes, export."""

import uuid
from datetime import datetime

import streamlit as st
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from pt_insights_os.db.duckdb_store import get_connection

st.set_page_config(page_title="Collections | PT Insights OS", page_icon="📁", layout="wide")


def load_data():
    conn = get_connection()
    threads = conn.execute("SELECT * FROM threads").fetchdf()
    posts = conn.execute("SELECT * FROM posts").fetchdf()
    collections = conn.execute("SELECT * FROM collections").fetchdf()
    items = conn.execute("SELECT * FROM collection_items").fetchdf()
    conn.close()
    return threads, posts, collections, items


def create_collection(name: str, description: str):
    conn = get_connection()
    coll_id = f"coll_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO collections VALUES (?, ?, ?, ?)",
        [coll_id, name, description, datetime.now()],
    )
    conn.close()
    return coll_id


def add_to_collection(collection_id: str, thread_id: str, note: str = ""):
    conn = get_connection()
    item_id = f"ci_{uuid.uuid4().hex[:12]}"
    conn.execute(
        "INSERT INTO collection_items VALUES (?, ?, ?, ?, ?)",
        [item_id, collection_id, thread_id, note, datetime.now()],
    )
    conn.close()


def remove_from_collection(item_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM collection_items WHERE item_id = ?", [item_id])
    conn.close()


def delete_collection(collection_id: str):
    conn = get_connection()
    conn.execute("DELETE FROM collection_items WHERE collection_id = ?", [collection_id])
    conn.execute("DELETE FROM collections WHERE collection_id = ?", [collection_id])
    conn.close()


threads, posts, collections, items = load_data()

# --- Header ---
st.markdown("""
<div style="background: linear-gradient(135deg, #0f3460, #16213e); padding: 1.5rem 2rem;
            border-radius: 14px; color: white; margin-bottom: 1.5rem;">
    <h2 style="margin:0; font-weight:700;">📁 Collections</h2>
    <p style="margin:0.25rem 0 0; opacity:0.8; font-size:0.9rem;">
        Organize threads into named collections — add notes and export
    </p>
</div>
""", unsafe_allow_html=True)

# --- Create New Collection ---
with st.expander("Create New Collection", expanded=False):
    col1, col2 = st.columns([2, 1])
    with col1:
        new_name = st.text_input("Collection Name", placeholder="e.g., Cash-Based Research")
        new_desc = st.text_input("Description", placeholder="Threads about transitioning to cash pay")
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Create Collection", type="primary", use_container_width=True):
            if new_name:
                create_collection(new_name, new_desc)
                st.success(f"Created collection: {new_name}")
                st.rerun()
            else:
                st.error("Please enter a name")

st.divider()

# --- Existing Collections ---
if collections.empty:
    st.markdown("""
    <div style="text-align:center; padding:3rem; color:#888;">
        <div style="font-size:2rem; margin-bottom:0.5rem;">📁</div>
        <p>No collections yet. Create one above to start organizing threads.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    text_col = "text_redacted" if "text_redacted" in posts.columns else "text"

    for _, coll in collections.iterrows():
        coll_items = items[items["collection_id"] == coll["collection_id"]]
        item_count = len(coll_items)

        with st.expander(f"**{coll['name']}** ({item_count} threads) — {coll.get('description', '')}", expanded=True):
            # Show items
            if not coll_items.empty:
                for _, item in coll_items.iterrows():
                    thread_posts = posts[posts["thread_id"] == item["thread_id"]]
                    preview = str(thread_posts.iloc[0][text_col])[:200] if not thread_posts.empty else "No content"

                    st.markdown(f"""
                    <div style="background:white; border-radius:8px; padding:0.75rem; margin:0.25rem 0;
                                box-shadow:0 1px 4px rgba(0,0,0,0.04); border-left:3px solid #0f3460;">
                        <div style="font-size:0.85rem; line-height:1.4;">{preview}...</div>
                        <div style="font-size:0.7rem; color:#888; margin-top:0.25rem;">
                            Thread {item['thread_id']}
                            {f' &bull; Note: {item["note"]}' if item.get("note") else ''}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"Remove", key=f"rm_{item['item_id']}"):
                        remove_from_collection(item["item_id"])
                        st.rerun()
            else:
                st.info("No threads in this collection yet.")

            # Add thread to collection
            st.markdown("**Add Thread:**")
            acol1, acol2, acol3 = st.columns([2, 2, 1])
            with acol1:
                thread_options = {}
                for _, t in threads.iterrows():
                    tp = posts[posts["thread_id"] == t["thread_id"]]
                    prev = str(tp.iloc[0][text_col])[:60] if not tp.empty else "..."
                    thread_options[f"{t['thread_id']} — {prev}..."] = t["thread_id"]
                selected_thread = st.selectbox(
                    "Thread", list(thread_options.keys()),
                    key=f"add_{coll['collection_id']}"
                )
            with acol2:
                note = st.text_input("Note", key=f"note_{coll['collection_id']}", placeholder="Optional note")
            with acol3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Add", key=f"addbtn_{coll['collection_id']}", type="primary"):
                    add_to_collection(coll["collection_id"], thread_options[selected_thread], note)
                    st.rerun()

            # Export
            st.markdown("---")
            ecol1, ecol2 = st.columns(2)
            with ecol1:
                if st.button("Export as Markdown", key=f"exp_{coll['collection_id']}"):
                    md = f"# {coll['name']}\n\n{coll.get('description', '')}\n\n"
                    for _, item in coll_items.iterrows():
                        tp = posts[posts["thread_id"] == item["thread_id"]]
                        for _, p in tp.iterrows():
                            md += f"## Thread {item['thread_id']}\n\n"
                            md += f"{p[text_col]}\n\n"
                            md += f"*Post {p['post_id']}*\n\n---\n\n"
                    st.download_button(
                        "Download .md", md,
                        file_name=f"{coll['name'].lower().replace(' ', '_')}.md",
                        key=f"dl_{coll['collection_id']}"
                    )
            with ecol2:
                if st.button("Delete Collection", key=f"del_{coll['collection_id']}"):
                    delete_collection(coll["collection_id"])
                    st.rerun()
