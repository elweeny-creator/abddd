# PT Insights OS

Analytics platform for Physical Therapy community data (Uncaged Clinician Facebook group).
Stack: Python 3.11+, DuckDB, Streamlit, sentence-transformers, FAISS, pandas, pyarrow.

## Key Commands

```
make install    # Install dependencies
make ingest     # Ingest raw data → DuckDB + Parquet
make enrich     # Run taxonomy tagging, metrics, entity extraction
make index      # Build search index (embeddings + FAISS/DuckDB)
make app        # Launch Streamlit app
make test       # Run pytest suite
make lint       # Run ruff + black checks
```

## Data Layout

- `data/raw/` — Raw Facebook exports (CSV/JSON/NDJSON/HTML). Gitignored.
- `data/processed/` — Parquet outputs. Gitignored.
- `data/warehouse/` — DuckDB database (`pt_insights.duckdb`). Gitignored.

## Rules

- All summaries must be extractive with source IDs — no free-form generation.
- Always use `text_redacted` — never expose `text_raw` in any UI or output.
- No overengineering — solve the stated problem minimally.
- Run `make test && make lint` before committing.
- Detailed domain knowledge lives in `docs/` (schema, taxonomy, tagging rules).
