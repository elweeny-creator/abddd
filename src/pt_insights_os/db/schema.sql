-- PT Insights OS — DuckDB Schema

CREATE TABLE IF NOT EXISTS threads (
    thread_id VARCHAR PRIMARY KEY,
    title VARCHAR,
    author_id_hash VARCHAR,
    created_at TIMESTAMP,
    post_count INTEGER DEFAULT 0,
    participant_count INTEGER DEFAULT 0,
    total_reactions INTEGER DEFAULT 0,
    url VARCHAR
);

CREATE TABLE IF NOT EXISTS posts (
    post_id VARCHAR PRIMARY KEY,
    thread_id VARCHAR,
    comment_id VARCHAR,
    parent_id VARCHAR,
    author_id_hash VARCHAR,
    created_at TIMESTAMP,
    text_redacted VARCHAR,
    text_raw VARCHAR,
    pii_spans JSON,
    redaction_version INTEGER,
    reactions INTEGER DEFAULT 0,
    reply_count INTEGER DEFAULT 0,
    url VARCHAR,
    media_flag BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS entities (
    entity_id VARCHAR PRIMARY KEY,
    post_id VARCHAR,
    entity_type VARCHAR,
    entity_value VARCHAR,
    confidence FLOAT
);

CREATE TABLE IF NOT EXISTS tags (
    tag_id VARCHAR PRIMARY KEY,
    l1_domain VARCHAR,
    l2_subdomain VARCHAR,
    l3_tag VARCHAR,
    description VARCHAR
);

CREATE TABLE IF NOT EXISTS tag_assignments (
    assignment_id VARCHAR PRIMARY KEY,
    post_id VARCHAR,
    tag_id VARCHAR,
    confidence FLOAT,
    source VARCHAR  -- 'rule', 'embedding', 'llm'
);

CREATE TABLE IF NOT EXISTS embeddings_index_meta (
    index_id VARCHAR PRIMARY KEY,
    model_name VARCHAR,
    backend VARCHAR,
    chunk_count INTEGER,
    created_at TIMESTAMP,
    index_path VARCHAR
);

CREATE TABLE IF NOT EXISTS collections (
    collection_id VARCHAR PRIMARY KEY,
    name VARCHAR,
    description VARCHAR,
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS collection_items (
    item_id VARCHAR PRIMARY KEY,
    collection_id VARCHAR,
    thread_id VARCHAR,
    note VARCHAR,
    added_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qa_audit (
    audit_id VARCHAR PRIMARY KEY,
    check_name VARCHAR,
    status VARCHAR,  -- 'pass', 'fail', 'warn'
    details VARCHAR,
    run_at TIMESTAMP
);

-- Enrichment columns on posts (added via ALTER if not exists)
-- thread_quality_score, novelty_score, disagreement_score,
-- actionable_density, owner_relevance_score, burnout_signal_score,
-- intent_type, business_stage, setting_type
