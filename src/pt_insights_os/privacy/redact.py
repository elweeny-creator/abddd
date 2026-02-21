"""PII redaction: regex-first, optional Presidio fallback."""

import json

import pandas as pd

from pt_insights_os.config import ENABLE_PRESIDIO, REDACTION_VERSION
from pt_insights_os.logging_config import setup_logging
from pt_insights_os.privacy.pii_rules import PII_PATTERNS

logger = setup_logging()

# Try to load Presidio if configured
_presidio_analyzer = None
if ENABLE_PRESIDIO == "auto" or ENABLE_PRESIDIO == "true":
    try:
        from presidio_analyzer import AnalyzerEngine

        _presidio_analyzer = AnalyzerEngine()
        logger.info("Presidio analyzer loaded")
    except ImportError:
        if ENABLE_PRESIDIO == "true":
            logger.warning("Presidio requested but not installed")
        else:
            logger.info("Presidio not available, using regex-only redaction")


def find_pii_spans(text: str) -> list[dict]:
    """Find PII spans using regex patterns + optional Presidio."""
    spans = []

    # Regex-first pass
    for label, pattern in PII_PATTERNS:
        for match in pattern.finditer(text):
            spans.append(
                {
                    "type": label,
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group(),
                    "source": "regex",
                }
            )

    # Presidio pass (if available)
    if _presidio_analyzer is not None:
        try:
            results = _presidio_analyzer.analyze(text=text, language="en")
            for r in results:
                # Avoid duplicates with regex spans
                overlaps = any(
                    s["start"] <= r.start < s["end"] or s["start"] < r.end <= s["end"]
                    for s in spans
                )
                if not overlaps:
                    spans.append(
                        {
                            "type": r.entity_type,
                            "start": r.start,
                            "end": r.end,
                            "text": text[r.start : r.end],
                            "source": "presidio",
                        }
                    )
        except Exception as e:
            logger.warning(f"Presidio analysis failed: {e}")

    # Sort by start position
    spans.sort(key=lambda s: s["start"])
    return spans


def redact_text(text: str) -> tuple[str, list[dict]]:
    """Redact PII from text. Returns (redacted_text, pii_spans)."""
    if not text or pd.isna(text):
        return "", []

    spans = find_pii_spans(text)
    if not spans:
        return text, []

    # Build redacted text by replacing spans (right-to-left to preserve positions)
    redacted = text
    for span in reversed(spans):
        replacement = f"[{span['type']}_REDACTED]"
        redacted = redacted[: span["start"]] + replacement + redacted[span["end"] :]

    return redacted, spans


def redact_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply redaction to all text fields in a DataFrame."""
    logger.info(f"Redacting PII from {len(df)} rows")

    redacted_texts = []
    pii_spans_list = []

    for text in df["text"]:
        redacted, spans = redact_text(str(text) if text else "")
        redacted_texts.append(redacted)
        # Store spans without the raw text for privacy
        clean_spans = [
            {"type": s["type"], "start": s["start"], "end": s["end"], "source": s["source"]}
            for s in spans
        ]
        pii_spans_list.append(json.dumps(clean_spans))

    df = df.copy()
    df["text_raw"] = df["text"]
    df["text_redacted"] = redacted_texts
    df["pii_spans"] = pii_spans_list
    df["redaction_version"] = REDACTION_VERSION

    # Drop original text column — downstream always uses text_redacted
    df = df.drop(columns=["text"])

    pii_count = sum(1 for spans in pii_spans_list if spans != "[]")
    logger.info(f"Redacted PII in {pii_count} rows")

    return df
