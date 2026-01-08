#!/usr/bin/env python3
"""
Convert the raw Facebook scraper JSON to clean JSONL format.
"""
import json
import re
import hashlib
from datetime import datetime
from pathlib import Path

INPUT_JSON = "dataset_facebook-post-scraper_2026-01-08_06-15-54-528.json"
OUTPUT_DIR = Path("/mnt/data")

def clean_text(text):
    """Basic text cleaning."""
    if not text:
        return ""
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def generate_thread_id(url, created_at):
    """Generate a stable thread ID from URL."""
    # Extract permalink ID from URL
    match = re.search(r'/permalink/(\d+)', url)
    if match:
        return f"thread_{match.group(1)}"
    # Fallback to hash
    return f"thread_{hashlib.md5(f'{url}{created_at}'.encode()).hexdigest()[:12]}"

def generate_comment_id(comment_url, thread_id, idx):
    """Generate a stable comment ID."""
    if comment_url:
        match = re.search(r'comment_id=(\d+)', comment_url)
        if match:
            return f"comment_{match.group(1)}"
    return f"{thread_id}_comment_{idx}"

def main():
    print(f"Loading {INPUT_JSON}...")
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"Loaded {len(data)} threads")

    threads = []
    all_comments = []

    for item in data:
        created_ts = item.get('createdAt', 0)
        created_iso = datetime.utcfromtimestamp(created_ts).isoformat() + 'Z' if created_ts else None

        thread_id = generate_thread_id(item.get('url', ''), created_ts)

        text_raw = item.get('text', '')
        text_clean = clean_text(text_raw)

        # Process comments
        comments = []
        for idx, c in enumerate(item.get('topComments', [])):
            c_created_ts = c.get('createdAt', 0)
            c_created_iso = datetime.utcfromtimestamp(c_created_ts).isoformat() + 'Z' if c_created_ts else None
            comment_id = generate_comment_id(c.get('url'), thread_id, idx)

            comment_obj = {
                'comment_id': comment_id,
                'thread_id': thread_id,
                'createdAt_iso': c_created_iso,
                'url': c.get('url', ''),
                'author_name': c.get('author', {}).get('name', ''),
                'text_raw': c.get('text', ''),
                'text_clean': clean_text(c.get('text', '')),
            }
            comments.append(comment_obj)
            all_comments.append(comment_obj)

        thread = {
            'thread_id': thread_id,
            'createdAt_iso': created_iso,
            'createdAt_ts': created_ts,
            'url': item.get('url', ''),
            'author_name': item.get('user', {}).get('name', ''),
            'author_url': item.get('user', {}).get('url', ''),
            'text_raw': text_raw,
            'text_clean': text_clean,
            'metrics': {
                'reactionCount': item.get('reactionCount', 0),
                'shareCount': item.get('shareCount', 0),
                'commentCount': item.get('commentCount', 0),
            },
            'comments': comments,
            'groupId': item.get('groupId', ''),
        }
        threads.append(thread)

    # Sort by created date descending
    threads.sort(key=lambda x: x.get('createdAt_ts', 0), reverse=True)

    # Write threads JSONL
    threads_path = OUTPUT_DIR / "uncaged_threads_clean.jsonl"
    print(f"Writing {len(threads)} threads to {threads_path}...")
    with open(threads_path, 'w', encoding='utf-8') as f:
        for t in threads:
            f.write(json.dumps(t, ensure_ascii=False) + '\n')

    # Write comments JSONL
    comments_path = OUTPUT_DIR / "uncaged_comments_clean.jsonl"
    print(f"Writing {len(all_comments)} comments to {comments_path}...")
    with open(comments_path, 'w', encoding='utf-8') as f:
        for c in all_comments:
            f.write(json.dumps(c, ensure_ascii=False) + '\n')

    # Write stats
    date_range = [t['createdAt_iso'] for t in threads if t['createdAt_iso']]
    stats = {
        'threads_count': len(threads),
        'comments_count': len(all_comments),
        'date_min': min(date_range) if date_range else None,
        'date_max': max(date_range) if date_range else None,
        'total_reactions': sum(t['metrics']['reactionCount'] for t in threads),
        'total_comments': sum(t['metrics']['commentCount'] for t in threads),
        'total_shares': sum(t['metrics']['shareCount'] for t in threads),
    }
    stats_path = OUTPUT_DIR / "uncaged_cleaning_stats.json"
    print(f"Writing stats to {stats_path}...")
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, indent=2, fp=f)

    print("Done!")
    print(f"Stats: {stats}")

if __name__ == "__main__":
    main()
