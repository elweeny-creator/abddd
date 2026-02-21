"""Tests for PII redaction."""

import json

import pandas as pd

from pt_insights_os.privacy.redact import find_pii_spans, redact_dataframe, redact_text


class TestPIIDetection:
    def test_detect_email(self):
        spans = find_pii_spans("Contact me at john@example.com for details")
        types = [s["type"] for s in spans]
        assert "EMAIL" in types

    def test_detect_phone(self):
        spans = find_pii_spans("Call me at (555) 123-4567")
        types = [s["type"] for s in spans]
        assert "PHONE" in types

    def test_detect_phone_with_country_code(self):
        spans = find_pii_spans("My number is +1 555-123-4567")
        types = [s["type"] for s in spans]
        assert "PHONE" in types

    def test_detect_address(self):
        spans = find_pii_spans("My office is at 123 Main Street")
        types = [s["type"] for s in spans]
        assert "ADDRESS" in types

    def test_detect_ssn(self):
        spans = find_pii_spans("SSN is 123-45-6789")
        types = [s["type"] for s in spans]
        assert "SSN" in types

    def test_detect_npi(self):
        spans = find_pii_spans("My NPI: 1234567890")
        types = [s["type"] for s in spans]
        assert "NPI" in types

    def test_detect_patient_id(self):
        spans = find_pii_spans("Patient ID: ABC123")
        types = [s["type"] for s in spans]
        assert "PATIENT_ID" in types

    def test_no_false_positives_on_clean_text(self):
        spans = find_pii_spans("Physical therapy is great for recovery after knee surgery")
        assert len(spans) == 0


class TestRedaction:
    def test_email_redacted(self):
        text = "Email me at doctor@clinic.com"
        redacted, spans = redact_text(text)
        assert "doctor@clinic.com" not in redacted
        assert "[EMAIL_REDACTED]" in redacted

    def test_phone_redacted(self):
        text = "Call (555) 123-4567 for appointment"
        redacted, spans = redact_text(text)
        assert "(555) 123-4567" not in redacted
        assert "[PHONE_REDACTED]" in redacted

    def test_multiple_pii_redacted(self):
        text = "Email: test@test.com Phone: 555-123-4567"
        redacted, spans = redact_text(text)
        assert "test@test.com" not in redacted
        assert "555-123-4567" not in redacted
        assert len(spans) >= 2

    def test_empty_text(self):
        redacted, spans = redact_text("")
        assert redacted == ""
        assert spans == []

    def test_none_text(self):
        redacted, spans = redact_text(None)
        assert redacted == ""
        assert spans == []

    def test_spans_have_correct_fields(self):
        text = "My email is test@example.com"
        _, spans = redact_text(text)
        assert len(spans) > 0
        span = spans[0]
        assert "type" in span
        assert "start" in span
        assert "end" in span


class TestDataFrameRedaction:
    def test_redact_dataframe(self):
        df = pd.DataFrame(
            {
                "post_id": ["p1", "p2"],
                "text": [
                    "Email me at doc@clinic.com",
                    "No PII here, just discussing PT techniques",
                ],
            }
        )
        result = redact_dataframe(df)

        assert "text_redacted" in result.columns
        assert "text_raw" in result.columns
        assert "pii_spans" in result.columns
        assert "redaction_version" in result.columns

        # Check email was redacted
        assert "doc@clinic.com" not in result.iloc[0]["text_redacted"]
        assert "[EMAIL_REDACTED]" in result.iloc[0]["text_redacted"]

        # Check clean text is preserved
        assert "PT techniques" in result.iloc[1]["text_redacted"]

        # Original text preserved in text_raw
        assert "doc@clinic.com" in result.iloc[0]["text_raw"]

    def test_pii_spans_are_valid_json(self):
        df = pd.DataFrame(
            {
                "post_id": ["p1"],
                "text": ["Contact: test@test.com or 555-123-4567"],
            }
        )
        result = redact_dataframe(df)
        spans = json.loads(result.iloc[0]["pii_spans"])
        assert isinstance(spans, list)
        assert len(spans) >= 2

    def test_no_raw_text_leaks_in_pii_spans(self):
        """PII spans should not contain the raw matched text."""
        df = pd.DataFrame(
            {
                "post_id": ["p1"],
                "text": ["Email: secret@hidden.com"],
            }
        )
        result = redact_dataframe(df)
        spans = json.loads(result.iloc[0]["pii_spans"])
        for span in spans:
            assert "text" not in span  # We strip raw text from stored spans


class TestZeroPIISurvival:
    """Critical: assert zero emails/phones survive in redacted text."""

    def test_no_emails_survive(self):
        import re

        texts = [
            "doc@clinic.com is my email",
            "reach me: first.last@hospital.org",
            "billing@ptpractice.net handles insurance",
            "No email here",
            "Multiple: a@b.com and c@d.com",
        ]
        df = pd.DataFrame({"post_id": [f"p{i}" for i in range(len(texts))], "text": texts})
        result = redact_dataframe(df)

        email_re = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
        for _, row in result.iterrows():
            assert not email_re.search(
                row["text_redacted"]
            ), f"Email survived in: {row['text_redacted']}"

    def test_no_phones_survive(self):
        import re

        texts = [
            "Call (555) 123-4567",
            "My number: 555.123.4567",
            "+1 555-123-4567",
            "No phone here",
            "Office: 800-555-0199",
        ]
        df = pd.DataFrame({"post_id": [f"p{i}" for i in range(len(texts))], "text": texts})
        result = redact_dataframe(df)

        phone_re = re.compile(
            r"(?<!\d)(?:\+?1[\s\-.]?)?(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}(?!\d)"
        )
        for _, row in result.iterrows():
            # Strip redaction markers before checking
            cleaned = re.sub(r"\[[A-Z_]+_REDACTED\]", "", row["text_redacted"])
            assert not phone_re.search(cleaned), f"Phone survived in: {row['text_redacted']}"
