# PT Insights OS

End-to-end analytics platform for Physical Therapy community data from the Uncaged Clinician Facebook group. Ingests raw exports, redacts PII, tags topics, computes engagement metrics, and surfaces insights through a Streamlit dashboard — all with zero hallucination and full source traceability.

## Quickstart

```bash
# Install
make install

# Run the full pipeline (generates synthetic data if none exists)
make ingest    # Ingest → normalize → redact → DuckDB + Parquet
make enrich    # Taxonomy tagging + metrics + entity extraction
make index     # Build search index

# Launch the app
make app       # Opens Streamlit on localhost:8501

# Quality checks
make test      # 84 tests across ingestion, redaction, enrichment, citations, search
make lint      # ruff + black
```

## Adding Your Data

Place Facebook export files in `data/raw/` (CSV, JSON, NDJSON, or HTML). Expected fields:

| Field | Required | Notes |
|-------|----------|-------|
| text / message / content | Yes | Post body |
| post_id / id | No | Auto-generated if missing |
| author / username | No | Hashed for privacy |
| created_at / timestamp | No | Parsed to datetime |
| reactions / likes | No | Defaults to 0 |
| reply_count | No | Defaults to 0 |
| thread_id | No | Defaults to post_id |
| parent_id / comment_id | No | For reply threading |

Then re-run the pipeline:

```bash
make ingest && make enrich && make index && make app
```

## Architecture

```
data/raw/          →  Ingest   →  Normalize  →  Redact PII  →  DuckDB + Parquet
                                                                    ↓
                                                              Enrich (tags, metrics, entities)
                                                                    ↓
                                                              Index (embeddings + vector search)
                                                                    ↓
                                                              Streamlit App (7 pages)
```

### App Pages

1. **Overview** — KPIs, top themes, top owner-relevant threads
2. **Trends** — Topics over time, emerging topics, disagreement hotspots
3. **Topic Explorer** — Taxonomy tree with faceted filters
4. **Thread Deep Dive** — Full redacted thread with evidence-linked summary
5. **Search** — Keyword + semantic search with source traceability
6. **Collections** — Save threads into named groups, add notes, export
7. **Owner's Briefing** — Generate citation-backed markdown briefings

## Stack

- **Python 3.11+**, DuckDB, pandas, pyarrow
- **Streamlit** for the interactive dashboard
- **scikit-learn** TF-IDF for embeddings (sentence-transformers/FAISS optional)
- **ruff + black** for code quality

## Key Design Decisions

- **Zero hallucination**: Every summary bullet is a direct quote from source data, ending with `[thread_id:..., post_id:...]`
- **Privacy-first**: PII redacted via regex (+ optional Presidio), authors hashed, `text_raw` never exposed in UI
- **Deterministic-first tagging**: Rule-based keyword matching fires first (confidence 1.0), embedding similarity backstops, optional LLM behind feature flag
- **Extractive only**: No generative summaries — select sentences, cite sources

## Known Limitations

- **Embedding quality**: TF-IDF fallback is less semantic than sentence-transformers. Install `sentence-transformers` for better search results
- **Entity extraction**: Regex-based NER; install `spacy` for richer extraction
- **Presidio**: Auto-detected but not required. Install for broader PII coverage
- **LLM tagger**: Stub behind `ENABLE_LLM_TAGGER=true` flag — not implemented yet
- **Scale**: Tested with synthetic 10-post dataset. Performance with 10k+ posts not benchmarked

## Next Upgrades

- [ ] Sentence-transformers integration for production-quality semantic search
- [ ] LLM-based topic classifier (behind feature flag)
- [ ] spaCy NER for richer entity extraction
- [ ] Time-series analysis with more temporal data
- [ ] Export collections to PDF
- [ ] Caching layer for Streamlit performance at scale
