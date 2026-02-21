"""Regex patterns for PII detection."""

import re

# Email addresses
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")

# Phone numbers (US formats)
PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:"
    r"\+?1[\s\-.]?"
    r")?"
    r"(?:"
    r"\(?\d{3}\)?[\s\-.]?"
    r")"
    r"\d{3}[\s\-.]?\d{4}"
    r"(?!\d)"
)

# Street addresses (simplified — number + street name + type)
ADDRESS_PATTERN = re.compile(
    r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s+){1,3}"
    r"(?:St(?:reet)?|Ave(?:nue)?|Blvd|Boulevard|Dr(?:ive)?|Ln|Lane|Rd|Road|Way|Ct|Court|Pl|Place|Cir|Circle)\b",
    re.IGNORECASE,
)

# SSN
SSN_PATTERN = re.compile(r"\b\d{3}[\-\s]?\d{2}[\-\s]?\d{4}\b")

# Clinic/patient identifiers — patterns like "Patient ID: ABC123", "MRN: 12345"
# Requires an explicit delimiter (:, =, #) to avoid matching "PT techniques" etc.
PATIENT_ID_PATTERN = re.compile(
    r"(?:patient|mrn|medical record|chart)\s*(?:id|#|number|no\.?)?\s*[:=#]\s*[A-Za-z0-9\-]{2,20}",
    re.IGNORECASE,
)

# NPI numbers (10-digit provider identifiers)
NPI_PATTERN = re.compile(r"\bNPI\s*[:=#]?\s*\d{10}\b", re.IGNORECASE)

# All patterns with their labels
PII_PATTERNS = [
    ("EMAIL", EMAIL_PATTERN),
    ("PHONE", PHONE_PATTERN),
    ("ADDRESS", ADDRESS_PATTERN),
    ("SSN", SSN_PATTERN),
    ("PATIENT_ID", PATIENT_ID_PATTERN),
    ("NPI", NPI_PATTERN),
]
