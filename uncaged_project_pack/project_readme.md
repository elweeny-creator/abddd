# Uncaged Clinician Knowledge Base Pack

## What's In This Pack

This is a curated knowledge base of **9,569** posts from the Uncaged Clinician Facebook group, spanning **2022-05-11** to **2026-01-07**.

### Files Included

| File | Description |
|------|-------------|
| `project_readme.md` | This file - how to use the pack |
| `report.md` | Dataset overview, trends, and insights |
| `engagement_threads_top.csv` | Top 300 posts by engagement |
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
python build_evidence_pack.py \
    --input /mnt/data/uncaged_threads_clean.jsonl \
    --topic_index /mnt/data/uncaged_project_pack/topic_index.json \
    --query "your question here" \
    --k 60 \
    --out evidence_pack.jsonl
```

## Provenance

Every data point traces back to:
- `thread_id` - Unique thread identifier
- `url` - Direct link to the Facebook post
- `comment_id` / comment `url` - For comment-level data

**Always cite these when using information from this pack.**
