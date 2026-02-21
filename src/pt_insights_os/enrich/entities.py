"""Lightweight NER for PT domain entities: insurers, EMRs, CPT codes, etc."""

import re
import uuid

# Named entity patterns
ENTITY_PATTERNS = {
    "INSURER": [
        r"\bUnitedHealth(?:care)?\b",
        r"\bAetna\b",
        r"\bBlue Cross\b(?:\s+Blue Shield)?",
        r"\bBCBS\b",
        r"\bCigna\b",
        r"\bHumana\b",
        r"\bKaiser\b(?:\s+Permanente)?",
        r"\bTriCare\b",
        r"\bMedicare\b",
        r"\bMedicaid\b",
    ],
    "EMR": [
        r"\bWebPT\b",
        r"\bClinicient\b",
        r"\bNet Health\b",
        r"\bOptima\b",
        r"\bPrompt\b",
        r"\bSimplePractice\b",
        r"\bJane App\b",
        r"\bTherapyNotes\b",
        r"\bPractice Fusion\b",
        r"\bAthena(?:health)?\b",
    ],
    "CPT_CODE": [
        r"\b97\d{3}\b",  # PT CPT codes (97xxx)
        r"\bCPT\s+\d{5}\b",
    ],
    "CREDENTIAL": [
        r"\bDPT\b",
        r"\bMSPT\b",
        r"\bOCS\b",
        r"\bSCS\b",
        r"\bNCS\b",
        r"\bFAAOMPT\b",
        r"\bPTA\b",
        r"\bCLT\b",
    ],
    "ORGANIZATION": [
        r"\bAPTA\b",
        r"\bABPTRFE\b",
        r"\bABPTS\b",
    ],
    "REGULATION": [
        r"\bPECOS\b",
        r"\bCAQH\b",
        r"\bHIPAA\b",
        r"\bOSHA\b",
    ],
}

# Compile patterns
COMPILED_PATTERNS = {
    entity_type: [re.compile(p, re.IGNORECASE) for p in patterns]
    for entity_type, patterns in ENTITY_PATTERNS.items()
}


def extract_entities(text: str, post_id: str) -> list[dict]:
    """Extract named entities from text."""
    if not text:
        return []

    entities = []
    seen = set()

    for entity_type, patterns in COMPILED_PATTERNS.items():
        for pattern in patterns:
            for match in pattern.finditer(text):
                value = match.group().strip()
                key = (entity_type, value.lower())
                if key not in seen:
                    seen.add(key)
                    entities.append(
                        {
                            "entity_id": f"ent_{uuid.uuid4().hex[:12]}",
                            "post_id": post_id,
                            "entity_type": entity_type,
                            "entity_value": value,
                            "confidence": 1.0,
                        }
                    )

    return entities


def classify_intent(text: str) -> str:
    """Classify the intent type of a post."""
    if not text:
        return "unknown"

    text_lower = text.lower()

    if re.search(r"\?", text) and re.search(
        r"\b(?:how|what|where|when|who|has anyone|does anyone|should I)\b", text_lower
    ):
        return "question"
    if re.search(r"\b(?:tip|advice|recommend|suggest|consider|should|try)\b", text_lower):
        return "advice"
    if re.search(
        r"\b(?:I did|I made|I went|my experience|we switched|we dropped|made the switch|I switched)\b",
        text_lower,
    ):
        return "experience_share"
    if re.search(r"\b(?:hiring|looking for|job|position|opening)\b", text_lower):
        return "job_posting"
    if re.search(r"\b(?:frustrated|burnout|overwhelm|quit|stressed|exhausted)\b", text_lower):
        return "venting"
    if re.search(r"\b(?:congrat|success|achieved|milestone|proud)\b", text_lower):
        return "celebration"

    return "discussion"


def classify_business_stage(text: str) -> str:
    """Classify business stage from context clues."""
    if not text:
        return "unknown"

    text_lower = text.lower()

    if re.search(
        r"\b(?:starting|new|launch|open(?:ing)?|first year|planning to start)\b", text_lower
    ):
        return "startup"
    if re.search(r"\b(?:growing|expand|scale|second location|adding staff)\b", text_lower):
        return "growth"
    if re.search(r"\b(?:established|mature|10\+? years|veteran|experienced owner)\b", text_lower):
        return "established"
    if re.search(r"\b(?:exit|sell(?:ing)?|retire|transition out|succession)\b", text_lower):
        return "exit"

    return "unknown"


def classify_setting(text: str) -> str:
    """Classify practice setting type."""
    if not text:
        return "unknown"

    text_lower = text.lower()

    if re.search(r"\boutpatient\b", text_lower):
        return "outpatient"
    if re.search(r"\b(?:home health|mobile|in-home)\b", text_lower):
        return "home_health"
    if re.search(r"\b(?:inpatient|acute care|hospital)\b", text_lower):
        return "inpatient"
    if re.search(r"\b(?:SNF|skilled nursing|nursing home|long.?term)\b", text_lower):
        return "snf"
    if re.search(r"\b(?:school|pediatric|early intervention)\b", text_lower):
        return "school_based"
    if re.search(r"\b(?:travel|PRN|contract)\b", text_lower):
        return "travel_prn"

    return "unknown"
