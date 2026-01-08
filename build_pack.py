#!/usr/bin/env python3
"""
build_pack.py - Build the Uncaged Clinician Knowledge Base Pack

Usage:
    python build_pack.py --input /mnt/data/uncaged_threads_clean.jsonl --outdir /mnt/data/uncaged_project_pack --topn 300
"""

import argparse
import csv
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Try importing matplotlib for charts
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not available, charts will be skipped")


# ============================================================================
# Configuration
# ============================================================================

TOPIC_CONFIG = {
    "pricing": {
        "keywords": ["price", "pricing", "cost", "rate", "rates", "charge", "fee", "fees",
                     "cash pay", "cash-pay", "cash based", "out of pocket", "oop",
                     "eval", "evaluation", "follow up", "follow-up", "followup",
                     "package", "packages", "membership", "subscription",
                     "per session", "per visit", "per hour", "/hr", "hourly",
                     "what do you charge", "how much", "billing"],
    },
    "legal_compliance": {
        "keywords": ["legal", "compliance", "hipaa", "ada", "liability", "malpractice",
                     "insurance requirement", "license", "licensing", "regulations",
                     "medicare", "medicaid", "pllc", "llc", "s-corp", "s corp",
                     "lawyer", "attorney", "contract", "lawsuit", "sued", "audit",
                     "npi", "ein", "business entity", "incorporation"],
    },
    "marketing_first_clients": {
        "keywords": ["first client", "first patients", "getting started", "starting out",
                     "new practice", "launch", "opening", "grand opening",
                     "build caseload", "fill schedule", "grow practice", "patient acquisition",
                     "marketing", "advertis", "facebook ads", "google ads", "seo",
                     "social media", "instagram", "content", "blog", "website"],
    },
    "referrals_physicians": {
        "keywords": ["referral", "referrals", "physician", "doctor", "md", "do ",
                     "primary care", "pcp", "orthopedic", "ortho", "specialist",
                     "direct access", "self-refer", "script", "prescription",
                     "networking", "relationship", "lunch and learn"],
    },
    "tech_stack": {
        "keywords": ["emr", "ehr", "software", "app", "scheduling", "intake",
                     "payment processing", "stripe", "square", "venmo", "paypal",
                     "telehealth", "video", "zoom", "jane app", "practice better",
                     "hint health", "healthie", "simple practice", "intakeq",
                     "google workspace", "slack", "notion", "asana", "trello"],
    },
    "ceu_courses_certs": {
        "keywords": ["ceu", "ceus", "continuing education", "course", "courses",
                     "certification", "certificate", "certified", "credential",
                     "ocs", "scs", "faaompt", "dry needling", "idn", "trigger point",
                     "manual therapy", "manipulation", "thrust", "mckenzie", "mdt",
                     "pelvic", "vestibular", "concussion", "sports", "orthopedic",
                     "naiomt", "maitland", "mulligan", "iastm", "graston", "cupping"],
    },
    "embedded_in_gym": {
        "keywords": ["gym", "crossfit", "fitness", "trainer", "personal training",
                     "box", "strength", "conditioning", "weightlifting", "powerlifting",
                     "athletic", "sports performance", "embedded", "on-site", "onsite",
                     "co-located", "rent space", "sublease", "gym owner"],
    },
    "scaling_hiring": {
        "keywords": ["hire", "hiring", "employee", "contractor", "1099", "w2", "w-2",
                     "scale", "scaling", "grow", "growth", "expand", "expansion",
                     "staff", "staffing", "team", "associate", "partner", "partnership",
                     "multiple locations", "second location", "franchise"],
    },
    "failures_burnout": {
        "keywords": ["fail", "failed", "failure", "mistake", "regret", "lesson learned",
                     "burnout", "burned out", "burnt out", "stress", "overwhelm",
                     "quit", "quitting", "closing", "close practice", "give up",
                     "struggle", "struggling", "hard time", "difficult", "challenge",
                     "work life balance", "work-life"],
    },
}

# Credential patterns for resources extraction
CREDENTIAL_PATTERNS = [
    r'\bOCS\b', r'\bSCS\b', r'\bNCS\b', r'\bCCS\b', r'\bGCS\b', r'\bWCS\b', r'\bPCS\b',
    r'\bFAAOMPT\b', r'\bCOPT\b', r'\bCMPT\b', r'\bCIMT\b', r'\bDAAPT\b',
    r'\bDPT\b', r'\bMPT\b', r'\bPT\b', r'\bPTA\b', r'\bATC\b', r'\bCSCS\b',
    r'\bDN\b', r'\bIDN\b', r'\bFDN\b',  # Dry needling
]

# CEU/Course provider patterns
CEU_PROVIDER_PATTERNS = [
    r'NAIOMT', r'APTA', r'Herman\s*&?\s*Wallace', r'EIM', r'Institute of Physical Art',
    r'Maitland', r'Mulligan', r'McKenzie\s+Institute', r'MDT', r'OPTP',
    r'AAOMPT', r'Functional Movement', r'FMS', r'SFMA', r'Dry\s*Needling',
    r'Myopain', r'Integrative', r'Evidence in Motion', r'UW\s+Sports',
]

# Software/tool patterns
SOFTWARE_PATTERNS = [
    r'Jane\s*App', r'Jane\s+Health', r'Practice\s*Better', r'Hint\s*Health', r'Healthie',
    r'Simple\s*Practice', r'IntakeQ', r'WebPT', r'Clinicient', r'Kareo',
    r'Prompt', r'BetterPT', r'Heno', r'OptimisPT', r'TheraOffice',
    r'Stripe', r'Square', r'PayPal', r'Venmo', r'QuickBooks', r'Wave',
    r'Calendly', r'Acuity', r'Google\s*Workspace', r'Zoom', r'Notion',
]

# Marketing-relevant patterns
MARKETING_PATTERNS = [
    r'swipe', r'script', r'objection', r'elevator pitch', r'value proposition',
    r'call to action', r'cta', r'testimonial', r'case study', r'before.{1,10}after',
    r'referral', r'word of mouth', r'review', r'google review', r'social proof',
    r'offer', r'discount', r'promo', r'free consult', r'discovery call',
    r'email sequence', r'funnel', r'landing page', r'lead magnet',
    r'pain point', r'transformation', r'outcome', r'result',
]


# ============================================================================
# Utility Functions
# ============================================================================

def get_text(thread):
    """Get clean text from thread, falling back to raw."""
    return thread.get('text_clean') or thread.get('text_raw') or ''

def get_all_text(thread):
    """Get all text from thread and its comments."""
    texts = [get_text(thread)]
    for c in thread.get('comments', []):
        texts.append(c.get('text_clean') or c.get('text_raw') or '')
    return ' '.join(texts)

def extract_snippet(text, max_len=200):
    """Extract a snippet from text."""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + '...'

def canonicalize_url(url):
    """Canonicalize URL by removing tracking params."""
    if not url:
        return ''
    try:
        parsed = urlparse(url)
        # Remove tracking parameters
        params = parse_qs(parsed.query, keep_blank_values=True)
        params_clean = {k: v for k, v in params.items()
                       if not k.startswith('utm_') and k not in ['fbclid', 'gclid', 'ref', 'source']}
        query_clean = urlencode(params_clean, doseq=True) if params_clean else ''
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', query_clean, ''))
    except:
        return url

def extract_urls(text):
    """Extract URLs from text."""
    if not text:
        return []
    pattern = r'https?://[^\s<>"\')\]]+(?<![.,;:!?)])'
    urls = re.findall(pattern, text)
    # Clean trailing punctuation
    cleaned = []
    for url in urls:
        url = re.sub(r'[.,;:!?)]+$', '', url)
        if url:
            cleaned.append(canonicalize_url(url))
    return cleaned

def extract_domain(url):
    """Extract domain from URL."""
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower().replace('www.', '')
    except:
        return ''

def calculate_engagement(metrics):
    """Calculate total engagement score."""
    return (metrics.get('reactionCount', 0) +
            metrics.get('commentCount', 0) * 2 +
            metrics.get('shareCount', 0) * 3)


# ============================================================================
# Money Extraction
# ============================================================================

MONEY_CONTEXT_KEYWORDS = {
    'eval': ['eval', 'evaluation', 'initial', 'new patient', 'assessment'],
    'followup': ['follow up', 'follow-up', 'followup', 'subsequent', 'return'],
    'session': ['session', 'visit', 'appointment', 'treatment'],
    'hour': ['hour', 'hourly', '/hr', 'per hour'],
    'package': ['package', 'packages', 'bundle'],
    'membership': ['membership', 'monthly', 'subscription'],
    'cash': ['cash', 'cash pay', 'cash-pay', 'out of pocket', 'oop'],
}

def extract_money_mentions(text, window=50):
    """Extract money amounts from text with context."""
    if not text:
        return []

    mentions = []

    # Pattern for money amounts: $150, 150/hr, $150-200, 150 to 200, etc.
    patterns = [
        # $X or $X.XX
        r'\$\s*(\d{1,4}(?:\.\d{1,2})?)',
        # $X-Y or $X - $Y range
        r'\$\s*(\d{1,4})\s*[-–—]\s*\$?\s*(\d{1,4})',
        # X to Y dollars
        r'(\d{1,4})\s*to\s*(\d{1,4})\s*(?:dollars?)?',
        # X/hr or X per hour
        r'(\d{1,4})\s*/\s*hr',
        r'(\d{1,4})\s+per\s+hour',
        # X per session/visit
        r'(\d{1,4})\s+per\s+(?:session|visit)',
    ]

    text_lower = text.lower()

    for pattern in patterns:
        for match in re.finditer(pattern, text_lower):
            start = max(0, match.start() - window)
            end = min(len(text), match.end() + window)
            context = text[start:end]

            # Extract amount values
            groups = match.groups()
            amounts = [float(g) for g in groups if g and g.isdigit() or (g and re.match(r'^\d+\.?\d*$', g))]
            # Filter reasonable amounts (1 to 9999)
            amounts = [a for a in amounts if 1 <= a <= 9999]

            if not amounts:
                continue

            # Identify context tags
            context_tags = []
            context_lower = context.lower()
            for tag, keywords in MONEY_CONTEXT_KEYWORDS.items():
                if any(kw in context_lower for kw in keywords):
                    context_tags.append(tag)

            mentions.append({
                'matched_text': match.group(0),
                'amount_values': amounts,
                'context_tags': context_tags,
                'context_snippet': extract_snippet(context, 100),
            })

    return mentions


# ============================================================================
# Resource/Entity Extraction
# ============================================================================

def extract_entities(text):
    """Extract credentials, courses, software mentions."""
    if not text:
        return []

    entities = []
    text_upper = text.upper()

    # Credentials
    for pattern in CREDENTIAL_PATTERNS:
        for match in re.finditer(pattern, text_upper):
            entities.append({
                'entity': match.group(0),
                'category': 'credential',
            })

    # CEU providers
    for pattern in CEU_PROVIDER_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append({
                'entity': match.group(0),
                'category': 'ceu_provider',
            })

    # Software
    for pattern in SOFTWARE_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            entities.append({
                'entity': match.group(0),
                'category': 'software',
            })

    return entities


# ============================================================================
# Topic Scoring
# ============================================================================

def score_topic(text, topic_keywords):
    """Score text relevance to a topic based on keyword hits."""
    if not text:
        return 0
    text_lower = text.lower()
    score = 0
    for kw in topic_keywords:
        # Count occurrences
        count = len(re.findall(re.escape(kw.lower()), text_lower))
        score += count
    return score


# ============================================================================
# Main Processing
# ============================================================================

def process_threads(input_path, topn=300):
    """Process all threads and return aggregated data."""

    threads = []
    all_money_mentions = []
    all_urls = defaultdict(lambda: {'count': 0, 'thread_ids': [], 'urls': [], 'first_seen': None, 'last_seen': None})
    all_entities = defaultdict(lambda: {'count': 0, 'category': '', 'thread_ids': [], 'urls': []})
    marketing_candidates = []
    topic_scores = defaultdict(list)  # topic -> [(score, engagement, thread)]

    # Counters
    threads_by_month = Counter()
    engagement_values = []
    money_by_month = Counter()

    count = 0
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            thread = json.loads(line)
            threads.append(thread)

            thread_id = thread.get('thread_id', '')
            thread_url = thread.get('url', '')
            created_iso = thread.get('createdAt_iso', '')
            metrics = thread.get('metrics', {})

            # Parse date
            if created_iso:
                try:
                    dt = datetime.fromisoformat(created_iso.replace('Z', '+00:00'))
                    month_key = dt.strftime('%Y-%m')
                    threads_by_month[month_key] += 1
                except:
                    pass

            # Engagement
            eng = calculate_engagement(metrics)
            engagement_values.append(metrics.get('reactionCount', 0))

            # Get all text
            full_text = get_all_text(thread)
            post_text = get_text(thread)

            # --- Money mentions ---
            # From thread
            for m in extract_money_mentions(post_text):
                m['source_type'] = 'thread'
                m['thread_id'] = thread_id
                m['comment_id'] = ''
                m['createdAt_iso'] = created_iso
                m['url'] = thread_url
                m['text_snippet'] = extract_snippet(post_text)
                all_money_mentions.append(m)
                if created_iso:
                    try:
                        dt = datetime.fromisoformat(created_iso.replace('Z', '+00:00'))
                        money_by_month[dt.strftime('%Y-%m')] += 1
                    except:
                        pass

            # From comments
            for c in thread.get('comments', []):
                c_text = c.get('text_clean') or c.get('text_raw') or ''
                for m in extract_money_mentions(c_text):
                    m['source_type'] = 'comment'
                    m['thread_id'] = thread_id
                    m['comment_id'] = c.get('comment_id', '')
                    m['createdAt_iso'] = c.get('createdAt_iso', '')
                    m['url'] = c.get('url', '')
                    m['text_snippet'] = extract_snippet(c_text)
                    all_money_mentions.append(m)

            # --- URL extraction ---
            for url in extract_urls(full_text):
                domain = extract_domain(url)
                if not domain or domain.startswith('facebook.com') or domain.startswith('fb.'):
                    continue

                all_urls[url]['count'] += 1
                if len(all_urls[url]['thread_ids']) < 5:
                    all_urls[url]['thread_ids'].append(thread_id)
                    all_urls[url]['urls'].append(thread_url)
                all_urls[url]['domain'] = domain

                if created_iso:
                    if not all_urls[url]['first_seen'] or created_iso < all_urls[url]['first_seen']:
                        all_urls[url]['first_seen'] = created_iso
                    if not all_urls[url]['last_seen'] or created_iso > all_urls[url]['last_seen']:
                        all_urls[url]['last_seen'] = created_iso

            # --- Entity extraction ---
            for ent in extract_entities(full_text):
                key = ent['entity'].upper()
                all_entities[key]['count'] += 1
                all_entities[key]['category'] = ent['category']
                if len(all_entities[key]['thread_ids']) < 5:
                    all_entities[key]['thread_ids'].append(thread_id)
                    all_entities[key]['urls'].append(thread_url)

            # --- Marketing candidates ---
            marketing_score = 0
            tags_triggered = []
            for pattern in MARKETING_PATTERNS:
                if re.search(pattern, full_text, re.IGNORECASE):
                    marketing_score += 1
                    tags_triggered.append(pattern)

            if marketing_score >= 2 or eng >= 20:
                marketing_candidates.append({
                    'source_type': 'thread',
                    'thread_id': thread_id,
                    'comment_id': '',
                    'createdAt_iso': created_iso,
                    'url': thread_url,
                    'engagement': eng,
                    'tags_triggered': tags_triggered[:5],
                    'text_snippet': extract_snippet(post_text, 300),
                    'score': marketing_score + eng * 0.1,
                })

            # --- Topic scoring ---
            for topic, config in TOPIC_CONFIG.items():
                score = score_topic(full_text, config['keywords'])
                if score > 0:
                    topic_scores[topic].append((score, eng, thread))

            count += 1
            if count % 1000 == 0:
                print(f"  Processed {count} threads...")

    print(f"  Total threads processed: {count}")

    return {
        'threads': threads,
        'money_mentions': all_money_mentions,
        'urls': all_urls,
        'entities': all_entities,
        'marketing_candidates': marketing_candidates,
        'topic_scores': topic_scores,
        'threads_by_month': threads_by_month,
        'engagement_values': engagement_values,
        'money_by_month': money_by_month,
    }


def generate_outputs(data, outdir, topn):
    """Generate all output files."""

    threads = data['threads']

    # === A. project_readme.md ===
    print("Generating project_readme.md...")
    readme = """# Uncaged Clinician Knowledge Base Pack

## What's In This Pack

This is a curated knowledge base of **{thread_count:,}** posts from the Uncaged Clinician Facebook group, spanning **{date_min}** to **{date_max}**.

### Files Included

| File | Description |
|------|-------------|
| `project_readme.md` | This file - how to use the pack |
| `report.md` | Dataset overview, trends, and insights |
| `engagement_threads_top.csv` | Top {topn} posts by engagement |
| `money_mentions.csv` | All pricing/cost discussions |
| `links_all.csv` | External links shared in posts |
| `domains_top.csv` | Most frequently shared domains |
| `resources_entities.csv` | CEUs, credentials, software mentions |
| `marketing_swipe_file.csv` | High-value marketing content |
| `topic_index.json` | Topic map for automated evidence retrieval |

### Charts (PNG)
- `threads_over_time.png` - Posting activity trend
- `engagement_hist_reactions.png` - Distribution of reactions
- `top_domains.png` - Most shared external sites
- `money_mentions_over_time.png` - Pricing discussion trend

## How to Use This Pack

### The "Evidence Pack Only" Rule

When asking questions about cash-based PT practices, **always ground your answers in evidence from this pack**. Do not make up information or rely solely on general knowledge.

**Good prompt pattern:**
> "Based ONLY on the evidence in this knowledge pack, [your question]. Cite thread_id and URL for each claim."

### Example Query Prompts

#### Pricing & Packages
```
Based ONLY on the evidence pack, what are the most common pricing strategies for cash-based PT evaluations and follow-ups?
Include specific dollar amounts mentioned and cite thread_id + URL for each.
```

#### Legal & Compliance
```
Using only this evidence pack, what legal considerations and entity structures do cash-based PT owners discuss?
Focus on HIPAA, liability, and business entity types. Cite sources.
```

#### First Clients & Marketing
```
From this evidence pack only, what tactics have worked for cash-based PTs getting their first clients?
Include both online and offline strategies. Cite thread_id + URL.
```

#### CEUs, Courses & Certifications
```
Based on this pack, which certifications (OCS, SCS, FAAOMPT, dry needling, etc.) and CEU courses
do members recommend or discuss? Are they worth it? Cite specific discussions.
```

#### Tech Stack & Software
```
From this evidence pack, what EMR/scheduling/payment software do cash-based PTs recommend or use?
Cite specific recommendations with thread_id + URL.
```

#### Gym-Embedded / Fitness Partnerships
```
Using this pack only, what experiences and advice exist for PTs embedded in gyms or CrossFit boxes?
Include rent arrangements, referral flows, and challenges. Cite sources.
```

#### Scaling & Hiring
```
From this evidence pack, what do cash-based PT owners say about hiring employees vs contractors?
What about expanding to multiple locations? Cite thread_id + URL.
```

#### Failures & Lessons Learned
```
Based on this pack, what mistakes and failures do cash-based PT owners share?
What would they do differently? Include burnout discussions. Cite sources.
```

## Automated Evidence Retrieval

Use `build_evidence_pack.py` to automatically gather relevant threads for any query:

```bash
python build_evidence_pack.py \\
    --input /mnt/data/uncaged_threads_clean.jsonl \\
    --topic_index /mnt/data/uncaged_project_pack/topic_index.json \\
    --query "your question here" \\
    --k 60 \\
    --out evidence_pack.jsonl
```

## Provenance

Every data point traces back to:
- `thread_id` - Unique thread identifier
- `url` - Direct link to the Facebook post
- `comment_id` / comment `url` - For comment-level data

**Always cite these when using information from this pack.**
""".format(
        thread_count=len(threads),
        date_min=min(t['createdAt_iso'] for t in threads if t.get('createdAt_iso'))[:10],
        date_max=max(t['createdAt_iso'] for t in threads if t.get('createdAt_iso'))[:10],
        topn=topn,
    )

    with open(outdir / 'project_readme.md', 'w', encoding='utf-8') as f:
        f.write(readme)

    # === B. report.md ===
    print("Generating report.md...")

    total_reactions = sum(t['metrics'].get('reactionCount', 0) for t in threads)
    total_comments = sum(t['metrics'].get('commentCount', 0) for t in threads)
    avg_reactions = total_reactions / len(threads) if threads else 0
    avg_comments = total_comments / len(threads) if threads else 0

    # Engagement distribution
    engagements = [calculate_engagement(t['metrics']) for t in threads]
    engagements_sorted = sorted(engagements, reverse=True)
    p90 = engagements_sorted[int(len(engagements_sorted) * 0.1)] if engagements_sorted else 0
    p50 = engagements_sorted[int(len(engagements_sorted) * 0.5)] if engagements_sorted else 0

    report = """# Uncaged Clinician Dataset Report

## Dataset Overview

| Metric | Value |
|--------|-------|
| Total Threads | {thread_count:,} |
| Total Comments (in data) | {comment_count:,} |
| Date Range | {date_min} to {date_max} |
| Total Reactions | {total_reactions:,} |
| Total Comments (metadata) | {total_comments_meta:,} |

## Engagement Distribution

| Percentile | Engagement Score |
|------------|------------------|
| Top 10% | ≥ {p90} |
| Median (50%) | {p50} |
| Average Reactions | {avg_reactions:.1f} |
| Average Comments | {avg_comments:.1f} |

## Key Trends

### Posting Activity
See `threads_over_time.png` for the full trend.

Top 5 most active months:
{top_months}

### Pricing Discussions
Found **{money_count:,}** money/pricing mentions across threads and comments.
See `money_mentions.csv` for details and `money_mentions_over_time.png` for trends.

### External Resources
Found **{url_count:,}** unique external URLs shared.
Top domains (see `top_domains.png`):
{top_domains}

### Credentials & Courses
Found mentions of **{entity_count}** unique credentials, courses, and tools.
See `resources_entities.csv` for the full list.

### Marketing Insights
Identified **{marketing_count:,}** high-signal posts for marketing swipe files.
See `marketing_swipe_file.csv`.

## How to Use This Data

1. **For pricing research**: Start with `money_mentions.csv`, filter by `context_tags`
2. **For topic deep-dives**: Use `topic_index.json` with `build_evidence_pack.py`
3. **For marketing copy**: Mine `marketing_swipe_file.csv` for scripts and objections
4. **For tech decisions**: Check `resources_entities.csv` filtered by `category=software`
5. **For credential ROI**: Check `resources_entities.csv` filtered by `category=credential`

## Charts Reference

- `threads_over_time.png` - Monthly posting volume
- `engagement_hist_reactions.png` - Reaction count distribution
- `top_domains.png` - Most shared external domains
- `money_mentions_over_time.png` - Pricing discussion trend
""".format(
        thread_count=len(threads),
        comment_count=sum(len(t.get('comments', [])) for t in threads),
        date_min=min(t['createdAt_iso'] for t in threads if t.get('createdAt_iso'))[:10],
        date_max=max(t['createdAt_iso'] for t in threads if t.get('createdAt_iso'))[:10],
        total_reactions=total_reactions,
        total_comments_meta=total_comments,
        p90=p90,
        p50=p50,
        avg_reactions=avg_reactions,
        avg_comments=avg_comments,
        top_months='\n'.join(f"- {m}: {c:,} posts" for m, c in data['threads_by_month'].most_common(5)),
        money_count=len(data['money_mentions']),
        url_count=len(data['urls']),
        top_domains='\n'.join(f"- {d}: {c} links" for d, c in Counter(
            u['domain'] for u in data['urls'].values()
        ).most_common(10)),
        entity_count=len(data['entities']),
        marketing_count=len(data['marketing_candidates']),
    )

    with open(outdir / 'report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    # === C. engagement_threads_top.csv ===
    print("Generating engagement_threads_top.csv...")

    threads_ranked = sorted(threads,
                           key=lambda t: calculate_engagement(t['metrics']),
                           reverse=True)[:topn]

    with open(outdir / 'engagement_threads_top.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['rank', 'thread_id', 'createdAt_iso', 'url',
                        'reactionCount', 'commentCount', 'shareCount', 'text_snippet'])
        for i, t in enumerate(threads_ranked, 1):
            writer.writerow([
                i,
                t.get('thread_id', ''),
                t.get('createdAt_iso', ''),
                t.get('url', ''),
                t['metrics'].get('reactionCount', 0),
                t['metrics'].get('commentCount', 0),
                t['metrics'].get('shareCount', 0),
                extract_snippet(get_text(t), 200),
            ])

    # === D. money_mentions.csv ===
    print("Generating money_mentions.csv...")

    with open(outdir / 'money_mentions.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['source_type', 'thread_id', 'comment_id', 'createdAt_iso',
                        'url', 'matched_text', 'amount_values', 'context_tags', 'text_snippet'])
        for m in data['money_mentions']:
            writer.writerow([
                m.get('source_type', ''),
                m.get('thread_id', ''),
                m.get('comment_id', ''),
                m.get('createdAt_iso', ''),
                m.get('url', ''),
                m.get('matched_text', ''),
                '|'.join(str(a) for a in m.get('amount_values', [])),
                '|'.join(m.get('context_tags', [])),
                m.get('text_snippet', ''),
            ])

    # === E. links_all.csv + domains_top.csv ===
    print("Generating links_all.csv and domains_top.csv...")

    with open(outdir / 'links_all.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['url_canonical', 'domain', 'counts', 'sample_thread_ids',
                        'sample_urls', 'first_seen_iso', 'last_seen_iso'])
        for url, info in sorted(data['urls'].items(), key=lambda x: -x[1]['count']):
            writer.writerow([
                url,
                info.get('domain', ''),
                info.get('count', 0),
                '|'.join(info.get('thread_ids', [])[:5]),
                '|'.join(info.get('urls', [])[:5]),
                info.get('first_seen', ''),
                info.get('last_seen', ''),
            ])

    # Aggregate by domain
    domain_counts = defaultdict(lambda: {'count': 0, 'urls': []})
    for url, info in data['urls'].items():
        domain = info.get('domain', '')
        if domain:
            domain_counts[domain]['count'] += info['count']
            if len(domain_counts[domain]['urls']) < 5:
                domain_counts[domain]['urls'].append(url)

    with open(outdir / 'domains_top.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['domain', 'counts', 'sample_urls'])
        for domain, info in sorted(domain_counts.items(), key=lambda x: -x[1]['count'])[:100]:
            writer.writerow([
                domain,
                info['count'],
                '|'.join(info['urls'][:5]),
            ])

    # === F. resources_entities.csv ===
    print("Generating resources_entities.csv...")

    with open(outdir / 'resources_entities.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['entity', 'category', 'count_mentions', 'doc_count_threads',
                        'sample_thread_ids', 'sample_urls'])
        for entity, info in sorted(data['entities'].items(), key=lambda x: -x[1]['count']):
            writer.writerow([
                entity,
                info.get('category', ''),
                info.get('count', 0),
                len(set(info.get('thread_ids', []))),
                '|'.join(info.get('thread_ids', [])[:5]),
                '|'.join(info.get('urls', [])[:5]),
            ])

    # === G. marketing_swipe_file.csv ===
    print("Generating marketing_swipe_file.csv...")

    marketing_sorted = sorted(data['marketing_candidates'],
                             key=lambda x: -x.get('score', 0))[:500]

    with open(outdir / 'marketing_swipe_file.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['source_type', 'thread_id', 'comment_id', 'createdAt_iso',
                        'url', 'engagement', 'tags_triggered', 'text_snippet'])
        for m in marketing_sorted:
            writer.writerow([
                m.get('source_type', ''),
                m.get('thread_id', ''),
                m.get('comment_id', ''),
                m.get('createdAt_iso', ''),
                m.get('url', ''),
                m.get('engagement', 0),
                '|'.join(m.get('tags_triggered', [])),
                m.get('text_snippet', ''),
            ])

    # === H. topic_index.json ===
    print("Generating topic_index.json...")

    topic_index = {"topics": {}}

    for topic, config in TOPIC_CONFIG.items():
        scored = data['topic_scores'].get(topic, [])
        # Sort by combined score (relevance * 0.7 + engagement * 0.3)
        scored_sorted = sorted(scored,
                              key=lambda x: x[0] * 0.7 + x[1] * 0.3,
                              reverse=True)[:50]

        topic_index["topics"][topic] = {
            "keywords": config["keywords"],
            "top_thread_ids": [t['thread_id'] for _, _, t in scored_sorted],
            "top_urls": [t['url'] for _, _, t in scored_sorted],
        }

    with open(outdir / 'topic_index.json', 'w', encoding='utf-8') as f:
        json.dump(topic_index, f, indent=2)

    # === Charts ===
    if HAS_MATPLOTLIB:
        print("Generating charts...")

        # 1. threads_over_time.png
        try:
            months = sorted(data['threads_by_month'].keys())
            counts = [data['threads_by_month'][m] for m in months]

            fig, ax = plt.subplots(figsize=(12, 5))
            ax.bar(range(len(months)), counts, color='steelblue')
            ax.set_xticks(range(0, len(months), max(1, len(months)//12)))
            ax.set_xticklabels([months[i] for i in range(0, len(months), max(1, len(months)//12))],
                             rotation=45, ha='right')
            ax.set_xlabel('Month')
            ax.set_ylabel('Number of Posts')
            ax.set_title('Uncaged Clinician Posts Over Time')
            plt.tight_layout()
            plt.savefig(outdir / 'threads_over_time.png', dpi=150)
            plt.close()
        except Exception as e:
            print(f"  Warning: Could not generate threads_over_time.png: {e}")

        # 2. engagement_hist_reactions.png
        try:
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.hist(data['engagement_values'], bins=50, color='coral', edgecolor='white')
            ax.set_xlabel('Reaction Count')
            ax.set_ylabel('Frequency')
            ax.set_title('Distribution of Reactions per Post')
            ax.set_xlim(0, min(100, max(data['engagement_values']) if data['engagement_values'] else 100))
            plt.tight_layout()
            plt.savefig(outdir / 'engagement_hist_reactions.png', dpi=150)
            plt.close()
        except Exception as e:
            print(f"  Warning: Could not generate engagement_hist_reactions.png: {e}")

        # 3. top_domains.png
        try:
            top_doms = Counter(u['domain'] for u in data['urls'].values()).most_common(15)
            domains, counts = zip(*top_doms) if top_doms else ([], [])

            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(range(len(domains)), counts, color='seagreen')
            ax.set_yticks(range(len(domains)))
            ax.set_yticklabels(domains)
            ax.invert_yaxis()
            ax.set_xlabel('Number of Links')
            ax.set_title('Top 15 External Domains Shared')
            plt.tight_layout()
            plt.savefig(outdir / 'top_domains.png', dpi=150)
            plt.close()
        except Exception as e:
            print(f"  Warning: Could not generate top_domains.png: {e}")

        # 4. money_mentions_over_time.png
        try:
            months = sorted(data['money_by_month'].keys())
            counts = [data['money_by_month'][m] for m in months]

            fig, ax = plt.subplots(figsize=(12, 5))
            ax.plot(range(len(months)), counts, marker='o', color='darkgreen', linewidth=2)
            ax.fill_between(range(len(months)), counts, alpha=0.3, color='green')
            ax.set_xticks(range(0, len(months), max(1, len(months)//12)))
            ax.set_xticklabels([months[i] for i in range(0, len(months), max(1, len(months)//12))],
                             rotation=45, ha='right')
            ax.set_xlabel('Month')
            ax.set_ylabel('Pricing Mentions')
            ax.set_title('Money/Pricing Discussions Over Time')
            plt.tight_layout()
            plt.savefig(outdir / 'money_mentions_over_time.png', dpi=150)
            plt.close()
        except Exception as e:
            print(f"  Warning: Could not generate money_mentions_over_time.png: {e}")
    else:
        print("Skipping charts (matplotlib not available)")


def main():
    parser = argparse.ArgumentParser(description='Build Uncaged Clinician Knowledge Pack')
    parser.add_argument('--input', required=True, help='Path to threads JSONL file')
    parser.add_argument('--outdir', required=True, help='Output directory')
    parser.add_argument('--topn', type=int, default=300, help='Number of top threads to include')

    args = parser.parse_args()

    input_path = Path(args.input)
    outdir = Path(args.outdir)

    # Clean and create output directory
    if outdir.exists():
        print(f"Removing existing output directory: {outdir}")
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"Input: {input_path}")
    print(f"Output: {outdir}")
    print(f"Top N: {args.topn}")
    print()

    # Process
    print("Processing threads...")
    data = process_threads(input_path, args.topn)

    print()
    print("Generating outputs...")
    generate_outputs(data, outdir, args.topn)

    # Final summary
    print()
    print("=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)
    print()
    print(f"Output directory: {outdir}")
    print()
    print("Files generated:")
    for f in sorted(outdir.iterdir()):
        size = f.stat().st_size
        print(f"  {f.name}: {size:,} bytes")
    print()
    print("Sanity checks:")
    print(f"  - Threads processed: {len(data['threads']):,}")
    print(f"  - Money mentions: {len(data['money_mentions']):,}")
    print(f"  - Unique external URLs: {len(data['urls']):,}")
    print(f"  - Unique entities: {len(data['entities']):,}")
    print(f"  - Marketing candidates: {len(data['marketing_candidates']):,}")
    print(f"  - Topics indexed: {len(TOPIC_CONFIG)}")


if __name__ == "__main__":
    main()
