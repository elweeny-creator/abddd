"""Chunk posts into searchable segments."""

import re


def chunk_text(text: str, max_chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks for embedding."""
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []

    # Split on sentence boundaries first
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_chunk_size and current:
            chunks.append(current.strip())
            # Keep overlap from end of previous chunk
            words = current.split()
            overlap_words = words[-overlap:] if len(words) > overlap else words
            current = " ".join(overlap_words) + " " + sentence
        else:
            current = (current + " " + sentence).strip()

    if current.strip():
        chunks.append(current.strip())

    return chunks


def prepare_chunks(posts: list[dict]) -> list[dict]:
    """Prepare searchable chunks from posts with metadata."""
    all_chunks = []
    for post in posts:
        text = post.get("text_redacted", post.get("text", ""))
        if not text:
            continue

        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append({
                "chunk_id": f"{post['post_id']}_c{i}",
                "post_id": post["post_id"],
                "thread_id": post.get("thread_id", ""),
                "comment_id": post.get("comment_id"),
                "text": chunk,
            })

    return all_chunks
