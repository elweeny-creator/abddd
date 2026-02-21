.PHONY: install ingest enrich index app test lint clean

install:
	pip install -e ".[dev]"

install-all:
	pip install -e ".[all]"

ingest:
	python scripts/run_ingest.py

enrich:
	python scripts/run_enrich.py

index:
	python scripts/run_index.py

app:
	streamlit run src/pt_insights_os/app/Home.py

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/ scripts/
	black --check src/ tests/ scripts/

format:
	ruff check --fix src/ tests/ scripts/
	black src/ tests/ scripts/

clean:
	rm -rf data/warehouse/*.duckdb data/processed/*.parquet
