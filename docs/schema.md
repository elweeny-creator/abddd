# PT Insights OS — Database Schema

DuckDB database: `data/warehouse/pt_insights.duckdb`

## Tables

### threads
| Column | Type | Description |
|--------|------|-------------|
| thread_id | VARCHAR PK | Unique thread identifier |
| title | VARCHAR | Thread title (if available) |
| author_id_hash | VARCHAR | Salted SHA-256 hash of first author |
| created_at | TIMESTAMP | Thread creation timestamp |
| post_count | INTEGER | Number of posts in thread |
| participant_count | INTEGER | Distinct authors in thread |
| total_reactions | INTEGER | Sum of all reactions |
| url | VARCHAR | Original permalink |
| thread_quality_score | FLOAT | Composite quality metric (0-1) |
| novelty_score | FLOAT | Vocabulary uniqueness (0-1) |
| disagreement_score | FLOAT | Presence of contrasting opinions (0-1) |
| actionable_density | FLOAT | Fraction of actionable sentences (0-1) |
| owner_relevance_score | FLOAT | Relevance to practice owners (0-1) |
| burnout_signal_score | FLOAT | Burnout language detected (0-1) |

### posts
| Column | Type | Description |
|--------|------|-------------|
| post_id | VARCHAR PK | Unique post identifier |
| thread_id | VARCHAR | Parent thread |
| comment_id | VARCHAR | Comment ID (if reply) |
| parent_id | VARCHAR | Parent post (if reply) |
| author_id_hash | VARCHAR | Salted SHA-256 of author |
| created_at | TIMESTAMP | Post timestamp |
| text_redacted | VARCHAR | PII-redacted text (always use this) |
| text_raw | VARCHAR | Original text (never expose in UI) |
| pii_spans | JSON | Detected PII spans metadata |
| redaction_version | INTEGER | Version of redaction rules applied |
| reactions | INTEGER | Reaction count |
| reply_count | INTEGER | Number of replies |
| url | VARCHAR | Permalink |
| media_flag | BOOLEAN | Has attached media |
| actionable_density | FLOAT | Fraction of actionable sentences |
| burnout_signal_score | FLOAT | Burnout language detected |
| owner_relevance_score | FLOAT | Practice owner relevance |
| intent_type | VARCHAR | question, advice, experience_share, etc. |
| business_stage | VARCHAR | startup, growth, established, exit |
| setting_type | VARCHAR | outpatient, home_health, inpatient, etc. |

### tags
| Column | Type | Description |
|--------|------|-------------|
| tag_id | VARCHAR PK | Deterministic UUID from taxonomy path |
| l1_domain | VARCHAR | Top-level domain (e.g., "Reimbursement") |
| l2_subdomain | VARCHAR | Subdomain (e.g., "Billing & Coding") |
| l3_tag | VARCHAR | Specific tag (e.g., "cpt_codes") |
| description | VARCHAR | Optional description |

### tag_assignments
| Column | Type | Description |
|--------|------|-------------|
| assignment_id | VARCHAR PK | Unique assignment ID |
| post_id | VARCHAR | Tagged post |
| tag_id | VARCHAR | Assigned tag |
| confidence | FLOAT | Confidence score (1.0 for rules) |
| source | VARCHAR | "rule", "embedding", or "llm" |

### entities
| Column | Type | Description |
|--------|------|-------------|
| entity_id | VARCHAR PK | Unique entity ID |
| post_id | VARCHAR | Source post |
| entity_type | VARCHAR | INSURER, EMR, CPT_CODE, CREDENTIAL, etc. |
| entity_value | VARCHAR | Extracted entity text |
| confidence | FLOAT | Extraction confidence |

### collections
| Column | Type | Description |
|--------|------|-------------|
| collection_id | VARCHAR PK | Unique collection ID |
| name | VARCHAR | Collection name |
| description | VARCHAR | Description |
| created_at | TIMESTAMP | Creation time |

### collection_items
| Column | Type | Description |
|--------|------|-------------|
| item_id | VARCHAR PK | Unique item ID |
| collection_id | VARCHAR | Parent collection |
| thread_id | VARCHAR | Saved thread |
| note | VARCHAR | User-added note |
| added_at | TIMESTAMP | When added |

### embeddings_index_meta
| Column | Type | Description |
|--------|------|-------------|
| index_id | VARCHAR PK | Index build ID |
| model_name | VARCHAR | Embedding model/backend used |
| backend | VARCHAR | faiss or numpy |
| chunk_count | INTEGER | Number of indexed chunks |
| created_at | TIMESTAMP | Build timestamp |
| index_path | VARCHAR | Path to serialized index |

### qa_audit
| Column | Type | Description |
|--------|------|-------------|
| audit_id | VARCHAR PK | Audit check ID |
| check_name | VARCHAR | Check identifier |
| status | VARCHAR | pass, fail, or warn |
| details | VARCHAR | Check details/message |
| run_at | TIMESTAMP | When check ran |
