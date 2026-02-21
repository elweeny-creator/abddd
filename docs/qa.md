# PT Insights OS — QA & Quality Assurance

## Automated Checks

### PII Redaction QA
- **no_emails_in_redacted**: Scans all `text_redacted` for email patterns — must find zero
- **no_phones_in_redacted**: Scans all `text_redacted` for phone patterns — must find zero
- Results stored in `qa_audit` table after each ingestion run

### Citation Guard
- Every evidence bullet in summaries/briefings must contain `[thread_id:..., post_id:...]`
- `validate_citations()` function enforces this — briefings fail if any bullet lacks source IDs
- Tested in `tests/test_citation_guard.py`

### Extractive-Only Guarantee
- Summaries select top-scoring sentences directly from source text
- No generative/free-form claims allowed
- Test verifies each bullet sentence exists verbatim in source data

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| test_ingest.py | 14 | CSV/JSON/NDJSON ingest, normalization, ID generation, type casting |
| test_redaction.py | 19 | Email/phone/address/SSN/NPI detection, DataFrame redaction, zero-survival |
| test_enrichment.py | 24 | Taxonomy loading, rule matching, hybrid tagging, entity extraction, metrics |
| test_citation_guard.py | 13 | Extractive summary, citation validation, briefing format |
| test_search.py | 14 | Chunking, embedding, vector index, keyword/hybrid search |

## Running QA

```bash
# Full test suite
make test

# Lint checks
make lint

# Run pipeline with QA checks
make ingest    # Runs PII QA checks automatically
```

## Privacy Rules

1. **text_raw** is stored but NEVER exposed in any UI, export, or API response
2. **text_redacted** is the only text field used downstream
3. **author** names are hashed with salted SHA-256 → `author_id_hash`
4. **pii_spans** stores detection metadata (type, position) but NOT the raw matched text
5. PII patterns: email, phone, address, SSN, NPI, patient/chart IDs
