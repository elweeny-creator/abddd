"""Tests for data ingestion pipeline."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from pt_insights_os.io.ingest import (
    CANONICAL_COLUMNS,
    ingest_csv,
    ingest_directory,
    ingest_file,
    ingest_json,
    ingest_ndjson,
)
from pt_insights_os.io.normalize import normalize


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def sample_records():
    return [
        {
            "post_id": "p1",
            "author": "Test User",
            "created_at": "2024-01-01T10:00:00",
            "text": "This is a test post about PT practice.",
            "reactions": "5",
            "reply_count": "2",
        },
        {
            "post_id": "p2",
            "author": "Another User",
            "created_at": "2024-01-02T11:00:00",
            "text": "Second post about reimbursement issues.",
            "reactions": "10",
            "reply_count": "0",
        },
    ]


class TestCSVIngest:
    def test_basic_csv(self, tmp_dir, sample_records):
        path = tmp_dir / "test.csv"
        df = pd.DataFrame(sample_records)
        df.to_csv(path, index=False)

        result = ingest_csv(path)
        assert len(result) == 2
        assert "post_id" in result.columns
        assert result.iloc[0]["post_id"] == "p1"

    def test_csv_with_spaces_in_headers(self, tmp_dir):
        path = tmp_dir / "test.csv"
        path.write_text("Post ID,Author Name,Text\np1,Test,Hello\n")

        result = ingest_csv(path)
        assert "post_id" in result.columns
        assert "author_name" in result.columns


class TestJSONIngest:
    def test_json_array(self, tmp_dir, sample_records):
        path = tmp_dir / "test.json"
        with open(path, "w") as f:
            json.dump(sample_records, f)

        result = ingest_json(path)
        assert len(result) == 2

    def test_json_nested(self, tmp_dir, sample_records):
        path = tmp_dir / "test.json"
        with open(path, "w") as f:
            json.dump({"data": sample_records, "meta": "info"}, f)

        result = ingest_json(path)
        assert len(result) == 2


class TestNDJSONIngest:
    def test_ndjson(self, tmp_dir, sample_records):
        path = tmp_dir / "test.ndjson"
        with open(path, "w") as f:
            for record in sample_records:
                f.write(json.dumps(record) + "\n")

        result = ingest_ndjson(path)
        assert len(result) == 2


class TestFileDetection:
    def test_auto_detect_csv(self, tmp_dir, sample_records):
        path = tmp_dir / "data.csv"
        pd.DataFrame(sample_records).to_csv(path, index=False)
        result = ingest_file(path)
        assert len(result) == 2

    def test_auto_detect_json(self, tmp_dir, sample_records):
        path = tmp_dir / "data.json"
        with open(path, "w") as f:
            json.dump(sample_records, f)
        result = ingest_file(path)
        assert len(result) == 2

    def test_unsupported_format(self, tmp_dir):
        path = tmp_dir / "data.xyz"
        path.write_text("invalid")
        with pytest.raises(ValueError, match="Unsupported"):
            ingest_file(path)


class TestDirectoryIngest:
    def test_multi_file(self, tmp_dir, sample_records):
        # CSV file
        csv_path = tmp_dir / "data1.csv"
        pd.DataFrame(sample_records[:1]).to_csv(csv_path, index=False)

        # JSON file
        json_path = tmp_dir / "data2.json"
        with open(json_path, "w") as f:
            json.dump(sample_records[1:], f)

        result = ingest_directory(tmp_dir)
        assert len(result) == 2

    def test_empty_directory(self, tmp_dir):
        result = ingest_directory(tmp_dir)
        assert len(result) == 0
        assert set(CANONICAL_COLUMNS).issubset(set(result.columns))


class TestNormalization:
    def test_column_aliases(self, tmp_dir):
        path = tmp_dir / "test.json"
        records = [{"id": "p1", "message": "Hello", "username": "Alice", "timestamp": "2024-01-01"}]
        with open(path, "w") as f:
            json.dump(records, f)

        df = ingest_file(path)
        result = normalize(df)

        assert "post_id" in result.columns
        assert "text_raw" not in result.columns  # text exists before redaction
        assert result.iloc[0]["post_id"] == "p1"

    def test_generates_missing_ids(self, tmp_dir):
        path = tmp_dir / "test.json"
        records = [{"text": "No IDs here"}]
        with open(path, "w") as f:
            json.dump(records, f)

        df = ingest_file(path)
        result = normalize(df)

        assert result.iloc[0]["post_id"] is not None
        assert result.iloc[0]["post_id"] != ""

    def test_author_hashing(self, tmp_dir):
        path = tmp_dir / "test.json"
        records = [{"text": "Hello", "author": "Dr. Jane Smith"}]
        with open(path, "w") as f:
            json.dump(records, f)

        df = ingest_file(path)
        result = normalize(df)

        assert result.iloc[0]["author_id_hash"] != ""
        assert result.iloc[0]["author_id_hash"] != "Dr. Jane Smith"
        assert len(result.iloc[0]["author_id_hash"]) == 16  # hex digest

    def test_type_casting(self, tmp_dir):
        path = tmp_dir / "test.json"
        records = [{"text": "Hello", "reactions": "15", "reply_count": "3"}]
        with open(path, "w") as f:
            json.dump(records, f)

        df = ingest_file(path)
        result = normalize(df)

        assert result.iloc[0]["reactions"] == 15
        assert result.iloc[0]["reply_count"] == 3
