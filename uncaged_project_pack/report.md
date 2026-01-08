# Uncaged Clinician Dataset Report

## Dataset Overview

| Metric | Value |
|--------|-------|
| Total Threads | 9,569 |
| Total Comments (in data) | 11,846 |
| Date Range | 2022-05-11 to 2026-01-07 |
| Total Reactions | 50,140 |
| Total Comments (metadata) | 74,894 |

## Engagement Distribution

| Percentile | Engagement Score |
|------------|------------------|
| Top 10% | ≥ 47 |
| Median (50%) | 10 |
| Average Reactions | 5.2 |
| Average Comments | 7.8 |

## Key Trends

### Posting Activity
See `threads_over_time.png` for the full trend.

Top 5 most active months:
- 2024-01: 277 posts
- 2023-01: 270 posts
- 2023-03: 269 posts
- 2024-04: 254 posts
- 2022-08: 253 posts

### Pricing Discussions
Found **1,375** money/pricing mentions across threads and comments.
See `money_mentions.csv` for details and `money_mentions_over_time.png` for trends.

### External Resources
Found **193** unique external URLs shared.
Top domains (see `top_domains.png`):
- instagram.com: 22 links
- uncagedclinician.com: 17 links
- open.spotify.com: 9 links
- docs.google.com: 7 links
- cms.gov: 6 links
- youtu.be: 5 links
- l.facebook.com: 5 links
- indeed.com: 4 links
- podcasts.apple.com: 4 links
- apta.org: 4 links

### Credentials & Courses
Found mentions of **61** unique credentials, courses, and tools.
See `resources_entities.csv` for the full list.

### Marketing Insights
Identified **3,041** high-signal posts for marketing swipe files.
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
