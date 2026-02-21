"""Keyword/rule-based matching for taxonomy tags."""

import re

# Mapping: tag_id → list of keyword patterns (case-insensitive)
# These are deterministic rules that fire first before any ML-based tagging
TAG_RULES: dict[str, list[str]] = {
    # Clinical Practice
    "manual_therapy": [r"\bmanual therapy\b", r"\bmob(?:ilization)?\b", r"\bmanipulation\b"],
    "exercise_prescription": [r"\bexercise\s+(?:program|prescription|rx)\b", r"\bHEP\b"],
    "dry_needling": [r"\bdry needling\b", r"\bDN\b", r"\btrigger point\b"],
    "telehealth_delivery": [r"\btelehealth\b", r"\btelemed(?:icine)?\b", r"\bvirtual visit\b"],
    "outcome_measures": [r"\boutcome measure\b", r"\bFIM\b", r"\bODI\b", r"\bNPRS\b", r"\bDASH\b"],
    "orthopedic": [r"\bortho(?:pedic)?\b", r"\bmusculoskeletal\b", r"\bMSK\b"],
    "neurological": [r"\bneuro(?:logical)?\b", r"\bstroke\b", r"\bTBI\b", r"\bspinal cord\b"],
    "sports_medicine": [r"\bsports\s+(?:med|medicine|rehab)\b", r"\bathlet(?:e|ic)\b"],
    "pelvic_health": [r"\bpelvic\s+(?:health|floor)\b"],
    # Reimbursement
    "rate_negotiation": [r"\brate\s+negoti\w+\b", r"\brenegotiat\w+\b", r"\bfee schedule\b"],
    "cpt_codes": [r"\bCPT\b", r"\b971\d{2}\b", r"\b970\d{2}\b"],
    "claim_denials": [r"\bdeni(?:al|ed)\b", r"\bappeal\b", r"\brecoup\b"],
    "authorization": [r"\bauth(?:orization)?\b", r"\bprior auth\b", r"\bpre-?cert\b"],
    "medicare": [r"\bmedicare\b", r"\bCMS\b", r"\bMMAC\b"],
    "medicaid": [r"\bmedicaid\b"],
    "workers_comp": [r"\bwork(?:ers?)?\s*comp\b", r"\bWC\b", r"\bL&I\b"],
    "commercial_insurance": [
        r"\bcommercial\s+insurance\b",
        r"\bprivate\s+insurance\b",
        r"\bmanaged care\b",
    ],
    # Sales & Marketing
    "referral_building": [r"\breferral\b", r"\bphysician\s+(?:referral|relation)\b"],
    "direct_access": [r"\bdirect access\b"],
    "social_media": [r"\bsocial media\b", r"\bfacebook\b", r"\binstagram\b"],
    "website_seo": [r"\bSEO\b", r"\bwebsite\b", r"\bgoogle\s+(?:my business|maps|reviews)\b"],
    "online_reviews": [r"\breviews?\b", r"\byelp\b", r"\bgoogle\s+review\b"],
    # Operations
    "scheduling_optimization": [r"\bschedul(?:e|ing)\b", r"\bno[- ]show\b", r"\bcancellation\b"],
    "revenue_cycle": [r"\brevenue cycle\b", r"\bRCM\b", r"\bcollection rate\b"],
    "cash_flow": [r"\bcash flow\b", r"\baccounts receivable\b", r"\bA/R\b"],
    # Staffing
    "recruitment": [r"\brecruit(?:ing|ment)?\b", r"\bhir(?:e|ing)\b", r"\bjob\s+post\b"],
    "compensation_benchmarks": [
        r"\bsalary\b",
        r"\bcompensation\b",
        r"\bpay\s+(?:rate|range|scale)\b",
    ],
    "productivity_standards": [r"\bproductivity\b", r"\butilization\b", r"\bunits?\s+per\b"],
    "travel_pt": [r"\btravel\s+PT\b", r"\btravel(?:ing)?\s+therap\b"],
    "prn_staffing": [r"\bPRN\b", r"\bper diem\b", r"\bcontract\s+PT\b"],
    # Legal & Compliance
    "state_practice_act": [r"\bpractice act\b", r"\blicensure\b", r"\bstate board\b"],
    "direct_access_laws": [r"\bdirect access\b.*\blaw\b", r"\bdirect access\b.*\bstate\b"],
    "hipaa": [r"\bHIPAA\b", r"\bprivacy\s+(?:rule|violation)\b"],
    "malpractice": [r"\bmalpractice\b", r"\bliability\b", r"\bnegligence\b"],
    "non_compete": [r"\bnon[- ]?compete\b", r"\brestrictive covenant\b"],
    "provider_enrollment": [r"\bcredential(?:ing)?\b", r"\benrollment\b"],
    "pecos": [r"\bPECOS\b"],
    "caqh": [r"\bCAQH\b"],
    "npi_management": [r"\bNPI\b"],
    # Documentation
    "eval_documentation": [r"\beval(?:uation)?\s+(?:doc|note)\b", r"\binitial eval\b"],
    "medical_necessity": [r"\bmedical necessity\b", r"\bMN\b"],
    # EMR & Tech
    "webpt": [r"\bWebPT\b"],
    "clinicient": [r"\bClinicient\b"],
    "net_health": [r"\bNet Health\b", r"\bOptima\b"],
    "patient_portal": [r"\bpatient portal\b"],
    "exercise_apps": [r"\bexercise app\b", r"\bPT Pal\b", r"\bMedBridge HEP\b"],
    # Burnout
    "workload_stress": [r"\bburnout\b", r"\bstress\b", r"\boverwhelm\b", r"\bexhaust\b"],
    "documentation_burden": [r"\bdoc(?:umentation)?\s+burden\b", r"\bpaperwork\b"],
    "productivity_pressure": [r"\bproductivity\s+(?:pressure|demand|requirement)\b"],
    "work_life_balance": [r"\bwork[- ]life\s+balance\b", r"\bbalance\b.*\bwork\b"],
    "career_change": [r"\bcareer\s+change\b", r"\bleaving\s+PT\b", r"\bquit(?:ting)?\b"],
    # Negotiation
    "rate_increase": [r"\brate\s+increase\b", r"\braise\b.*\brate\b"],
    "salary_benchmarks": [r"\bsalary\b.*\bbenchmark\b", r"\bmarket\s+rate\b"],
    # Scaling
    "startup_planning": [r"\bstart(?:ing)?\s+(?:a\s+)?(?:practice|clinic|business)\b"],
    "buying_practice": [r"\bbuy(?:ing)?\s+(?:a\s+)?practice\b", r"\bacquisition\b"],
    "cash_based_transition": [
        r"\bcash[- ]?(?:based|pay)\b",
        r"\bout[- ]?of[- ]?network\b",
        r"\bOON\b",
    ],
    "mobile_practice": [r"\bmobile\s+(?:PT|practice|therapy)\b", r"\bhome\s+health\b"],
    "multi_location": [r"\bmulti[- ]?location\b", r"\bsecond\s+(?:clinic|location)\b"],
    # Referrals
    "md_relationships": [r"\bphysician\s+relationship\b", r"\bMD\s+referral\b"],
    "word_of_mouth": [r"\bword of mouth\b"],
    # Contracting
    "contract_review": [r"\bcontract\s+review\b", r"\bcontract\s+terms\b"],
    "network_participation": [r"\bin[- ]?network\b", r"\bpar(?:ticipating)?\s+provider\b"],
}

# Compile all patterns
COMPILED_RULES: dict[str, list[re.Pattern]] = {
    tag: [re.compile(p, re.IGNORECASE) for p in patterns] for tag, patterns in TAG_RULES.items()
}


def match_rules(text: str) -> list[tuple[str, float]]:
    """Match text against all tag rules. Returns list of (tag_id, confidence)."""
    matches = []
    for tag_id, patterns in COMPILED_RULES.items():
        for pattern in patterns:
            if pattern.search(text):
                matches.append((tag_id, 1.0))  # Rule-based = confidence 1.0
                break
    return matches
