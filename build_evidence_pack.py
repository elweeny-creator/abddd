#!/usr/bin/env python3
"""
build_evidence_pack.py - Build an evidence pack for a specific query

Usage:
    python build_evidence_pack.py \
        --input /mnt/data/uncaged_threads_clean.jsonl \
        --topic_index /mnt/data/uncaged_project_pack/topic_index.json \
        --query "CEU courses certifications worth it" \
        --k 60 \
        --out /mnt/data/uncaged_project_pack/evidence_pack.jsonl

The script is streaming-friendly and doesn't load the entire JSONL into memory.
"""

import argparse
import json
import re
from pathlib import Path
from collections import defaultdict


def get_text(thread):
    """Get clean text from thread, falling back to raw."""
    return thread.get('text_clean') or thread.get('text_raw') or ''


def get_comments_text(thread, max_comments=10):
    """Get text from top comments."""
    comments = thread.get('comments', [])[:max_comments]
    texts = []
    for c in comments:
        text = c.get('text_clean') or c.get('text_raw') or ''
        if text:
            texts.append(text)
    return texts


def calculate_engagement(metrics):
    """Calculate total engagement score."""
    return (metrics.get('reactionCount', 0) +
            metrics.get('commentCount', 0) * 2 +
            metrics.get('shareCount', 0) * 3)


def extract_keywords(query):
    """Extract keywords from query."""
    # Simple tokenization
    tokens = re.findall(r'\b[a-zA-Z0-9]+\b', query.lower())
    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were',
                  'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
                  'will', 'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                  'can', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by', 'from',
                  'as', 'into', 'through', 'during', 'before', 'after', 'above', 'below',
                  'it', 'its', 'this', 'that', 'these', 'those', 'what', 'which', 'who',
                  'whom', 'whose', 'when', 'where', 'why', 'how', 'all', 'each', 'every',
                  'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
                  'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'just',
                  'about', 'any', 'worth', 'get', 'getting'}
    keywords = [t for t in tokens if t not in stop_words and len(t) > 2]
    return keywords


def score_thread(thread, query_keywords, topic_keywords):
    """Score a thread's relevance to a query."""
    text = get_text(thread).lower()
    comments_text = ' '.join(get_comments_text(thread)).lower()
    full_text = text + ' ' + comments_text

    score = 0.0
    matched_keywords = []

    # Query keyword matching (higher weight)
    for kw in query_keywords:
        count = len(re.findall(r'\b' + re.escape(kw) + r'\b', full_text))
        if count > 0:
            score += count * 2.0
            matched_keywords.append(kw)

    # Topic keyword matching (from topic_index)
    for kw in topic_keywords:
        count = len(re.findall(re.escape(kw.lower()), full_text))
        if count > 0:
            score += count * 1.0
            if kw not in matched_keywords:
                matched_keywords.append(kw)

    # Engagement boost (log scale)
    engagement = calculate_engagement(thread.get('metrics', {}))
    if engagement > 0:
        import math
        score += math.log1p(engagement) * 0.5

    return score, matched_keywords


def find_best_matching_topics(query_keywords, topic_index):
    """Find topics that best match the query."""
    topic_scores = {}

    for topic_name, topic_data in topic_index.get('topics', {}).items():
        topic_kws = topic_data.get('keywords', [])
        overlap = sum(1 for kw in query_keywords if any(kw in tk.lower() for tk in topic_kws))
        if overlap > 0:
            topic_scores[topic_name] = overlap

    return sorted(topic_scores.items(), key=lambda x: -x[1])


def build_why_selected(matched_keywords, engagement, score):
    """Build a human-readable explanation of why this thread was selected."""
    parts = []
    if matched_keywords:
        parts.append(f"Matched keywords: {', '.join(matched_keywords[:5])}")
    if engagement > 10:
        parts.append(f"High engagement ({engagement})")
    parts.append(f"Relevance score: {score:.1f}")
    return "; ".join(parts)


def main():
    parser = argparse.ArgumentParser(description='Build evidence pack from query')
    parser.add_argument('--input', required=True, help='Path to threads JSONL file')
    parser.add_argument('--topic_index', required=True, help='Path to topic_index.json')
    parser.add_argument('--query', required=True, help='Free-text query')
    parser.add_argument('--k', type=int, default=60, help='Number of threads to return')
    parser.add_argument('--out', required=True, help='Output evidence pack path')

    args = parser.parse_args()

    input_path = Path(args.input)
    topic_index_path = Path(args.topic_index)
    output_path = Path(args.out)

    print(f"Query: {args.query}")
    print(f"Input: {input_path}")
    print(f"Topic index: {topic_index_path}")
    print(f"Output: {output_path}")
    print(f"K: {args.k}")
    print()

    # Load topic index
    print("Loading topic index...")
    with open(topic_index_path, 'r', encoding='utf-8') as f:
        topic_index = json.load(f)

    # Extract query keywords
    query_keywords = extract_keywords(args.query)
    print(f"Query keywords: {query_keywords}")

    # Find matching topics
    matching_topics = find_best_matching_topics(query_keywords, topic_index)
    print(f"Matching topics: {matching_topics[:3] if matching_topics else 'None'}")

    # Collect topic keywords from matching topics
    topic_keywords = set()
    topic_thread_ids = set()
    for topic_name, _ in matching_topics[:3]:
        topic_data = topic_index['topics'].get(topic_name, {})
        topic_keywords.update(topic_data.get('keywords', []))
        topic_thread_ids.update(topic_data.get('top_thread_ids', []))

    print(f"Topic keywords to use: {len(topic_keywords)}")
    print(f"Pre-selected thread IDs from topics: {len(topic_thread_ids)}")
    print()

    # Stream through input and score threads
    print("Scoring threads (streaming)...")
    scored_threads = []
    count = 0

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            thread = json.loads(line)
            thread_id = thread.get('thread_id', '')

            # Score thread
            score, matched_kws = score_thread(thread, query_keywords, topic_keywords)

            # Bonus for being in pre-selected topic threads
            if thread_id in topic_thread_ids:
                score += 5.0

            if score > 0:
                scored_threads.append({
                    'thread': thread,
                    'score': score,
                    'matched_keywords': matched_kws,
                })

            count += 1
            if count % 2000 == 0:
                print(f"  Processed {count} threads, found {len(scored_threads)} relevant...")

    print(f"  Total: {count} threads processed, {len(scored_threads)} relevant")
    print()

    # Sort by score and take top k
    scored_threads.sort(key=lambda x: -x['score'])
    top_threads = scored_threads[:args.k]

    print(f"Selected top {len(top_threads)} threads")
    print()

    # Write output
    print(f"Writing evidence pack to {output_path}...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        for item in top_threads:
            thread = item['thread']
            engagement = calculate_engagement(thread.get('metrics', {}))

            record = {
                'thread_id': thread.get('thread_id', ''),
                'url': thread.get('url', ''),
                'createdAt_iso': thread.get('createdAt_iso', ''),
                'metrics': thread.get('metrics', {}),
                'post_text': get_text(thread),
                'comments_text': get_comments_text(thread, max_comments=5),
                'why_selected': build_why_selected(
                    item['matched_keywords'],
                    engagement,
                    item['score']
                ),
            }
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

    # Summary
    print()
    print("=" * 60)
    print("EVIDENCE PACK COMPLETE")
    print("=" * 60)
    print()
    print(f"Query: {args.query}")
    print(f"Threads selected: {len(top_threads)}")
    print(f"Output: {output_path}")
    print()

    if top_threads:
        print("Top 5 threads by relevance:")
        for i, item in enumerate(top_threads[:5], 1):
            thread = item['thread']
            snippet = get_text(thread)[:100].replace('\n', ' ') + '...'
            print(f"  {i}. [{thread.get('thread_id', '')}] score={item['score']:.1f}")
            print(f"     {thread.get('url', '')}")
            print(f"     {snippet}")
            print()

    # Verify output
    output_size = output_path.stat().st_size
    with open(output_path, 'r', encoding='utf-8') as f:
        line_count = sum(1 for _ in f)

    print(f"Output file: {output_size:,} bytes, {line_count} records")


if __name__ == "__main__":
    main()
