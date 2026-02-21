"""Run the full ingestion pipeline: ingest → normalize → redact → load → export."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pt_insights_os.config import RAW_DATA_DIR
from pt_insights_os.db.duckdb_store import (
    export_parquet,
    get_connection,
    init_schema,
    rebuild_threads,
    run_qa_check,
    upsert_posts,
)
from pt_insights_os.io.ingest import ingest_directory
from pt_insights_os.io.normalize import normalize
from pt_insights_os.logging_config import setup_logging
from pt_insights_os.privacy.redact import redact_dataframe

logger = setup_logging()


def generate_sample_data(raw_dir: Path) -> None:
    """Generate synthetic sample data if no real data exists."""
    import json

    sample = [
        {
            "post_id": "post_001",
            "thread_id": "thread_001",
            "author": "Dr. Jane Smith",
            "created_at": "2024-01-15T10:30:00",
            "text": "Has anyone transitioned from insurance-based to cash-based PT? "
            "I'm considering making the switch for my clinic in Denver. "
            "Email me at jane.smith@ptclinic.com for details. "
            "My office is at 123 Main Street Denver.",
            "reactions": 15,
            "reply_count": 8,
        },
        {
            "post_id": "post_002",
            "thread_id": "thread_001",
            "parent_id": "post_001",
            "comment_id": "comment_001",
            "author": "Mike Johnson PT",
            "created_at": "2024-01-15T11:00:00",
            "text": "I made the switch 2 years ago. Best decision ever. "
            "Revenue went up 40% and I dropped from 35 patients/day to 12. "
            "Call me at (555) 123-4567 to chat about it. "
            "I use WebPT for my EMR and it handles cash-pay well.",
            "reactions": 22,
            "reply_count": 3,
        },
        {
            "post_id": "post_003",
            "thread_id": "thread_001",
            "parent_id": "post_001",
            "comment_id": "comment_002",
            "author": "Sarah Williams DPT",
            "created_at": "2024-01-15T12:15:00",
            "text": "Be careful with the transition. I lost 60% of my patients initially. "
            "It took 8 months to rebuild. Make sure you have 6 months of runway. "
            "Also check your state practice act — some states have restrictions on direct access.",
            "reactions": 18,
            "reply_count": 1,
        },
        {
            "post_id": "post_004",
            "thread_id": "thread_002",
            "author": "Tom Chen",
            "created_at": "2024-02-01T09:00:00",
            "text": "Burnout is real in outpatient PT. I'm seeing 28 patients a day "
            "and documenting until 9pm. Anyone else dealing with productivity requirements "
            "that feel unsustainable? My clinic owner says we need 90% utilization.",
            "reactions": 45,
            "reply_count": 15,
        },
        {
            "post_id": "post_005",
            "thread_id": "thread_002",
            "parent_id": "post_004",
            "comment_id": "comment_003",
            "author": "Linda Park OCS",
            "created_at": "2024-02-01T09:30:00",
            "text": "Same here. I've been looking at travel PT or PRN work just to escape "
            "the daily grind. The reimbursement from UnitedHealthcare and Aetna keeps "
            "dropping while productivity demands increase. CPT 97110 pays less every year.",
            "reactions": 30,
            "reply_count": 5,
        },
        {
            "post_id": "post_006",
            "thread_id": "thread_003",
            "author": "Rachel Ortiz",
            "created_at": "2024-02-10T14:00:00",
            "text": "Looking to hire a staff PT for my outpatient ortho clinic. "
            "We're in Austin TX, offering $85-95k + benefits. "
            "Must have ortho experience and manual therapy skills. "
            "Contact recruiting@austinpt.com or call 512-555-0199.",
            "reactions": 8,
            "reply_count": 4,
        },
        {
            "post_id": "post_007",
            "thread_id": "thread_003",
            "parent_id": "post_006",
            "comment_id": "comment_004",
            "author": "David Nguyen",
            "created_at": "2024-02-10T15:00:00",
            "text": "That salary range seems low for Austin market. "
            "New grads are getting $80k+ at the big chains. "
            "You might want to consider offering student loan assistance — "
            "average PT school debt is $150k now.",
            "reactions": 12,
            "reply_count": 2,
        },
        {
            "post_id": "post_008",
            "thread_id": "thread_004",
            "author": "Amy Foster MSPT",
            "created_at": "2024-03-05T08:00:00",
            "text": "Just negotiated a new contract with Blue Cross Blue Shield. "
            "They tried to cut our rates by 8%. We pushed back with outcomes data "
            "and actually got a 3% increase. Key was showing our readmission rates "
            "and patient satisfaction scores. Happy to share our template.",
            "reactions": 52,
            "reply_count": 20,
        },
        {
            "post_id": "post_009",
            "thread_id": "thread_005",
            "author": "Kevin Brown PT DPT",
            "created_at": "2024-03-15T10:00:00",
            "text": "Starting a mobile PT practice. Anyone have experience with "
            "credentialing for home health through Medicare? "
            "The PECOS enrollment process is confusing. "
            "NPI: 1234567890. My billing service recommended starting with "
            "Medicare Part B before adding commercial payers.",
            "reactions": 10,
            "reply_count": 6,
        },
        {
            "post_id": "post_010",
            "thread_id": "thread_005",
            "parent_id": "post_009",
            "comment_id": "comment_005",
            "author": "Maria Gonzalez",
            "created_at": "2024-03-15T11:30:00",
            "text": "PECOS is a nightmare but doable. Budget 90 days for the full process. "
            "Make sure your malpractice insurance covers mobile/home health visits. "
            "I use SimplePractice for scheduling and it works great for mobile providers.",
            "reactions": 8,
            "reply_count": 1,
        },
    ]

    sample_path = raw_dir / "sample_data.json"
    with open(sample_path, "w") as f:
        json.dump(sample, f, indent=2)
    logger.info(f"Generated sample data at {sample_path}")


def main():
    # Check for data
    supported = {".csv", ".json", ".ndjson", ".jsonl", ".html", ".htm"}
    has_data = any(
        f.suffix.lower() in supported
        for f in RAW_DATA_DIR.iterdir()
        if not f.name.startswith(".")
    ) if RAW_DATA_DIR.exists() else False

    if not has_data:
        logger.info("No raw data found, generating synthetic sample data")
        generate_sample_data(RAW_DATA_DIR)

    # Ingest
    logger.info("Starting ingestion pipeline")
    df = ingest_directory(RAW_DATA_DIR)
    logger.info(f"Ingested {len(df)} rows")

    # Normalize
    df = normalize(df)

    # Redact
    df = redact_dataframe(df)

    # Load to DuckDB
    conn = get_connection()
    init_schema(conn)
    upsert_posts(conn, df)
    rebuild_threads(conn)

    # Export Parquet
    export_parquet(conn)

    # QA checks
    checks = run_qa_check(conn)
    for check in checks:
        status = "✓" if check["status"] == "pass" else "✗"
        logger.info(f"QA {status} {check['check_name']}: {check['details']}")

    conn.close()
    logger.info("Ingestion pipeline complete")


if __name__ == "__main__":
    main()
