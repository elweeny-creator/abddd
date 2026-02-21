"""Extractive summarization — select top evidence sentences with mandatory citations."""

import re


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    if not text:
        return []
    # Split on sentence boundaries
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]


def _score_sentence(sentence: str) -> float:
    """Score a sentence for evidence value."""
    score = 0.0

    # Length bonus (prefer substantive sentences)
    words = len(sentence.split())
    if 10 <= words <= 40:
        score += 0.3
    elif words > 40:
        score += 0.1

    # Contains numbers/data
    if re.search(r"\d+%|\$\d+|\d+\s+(?:patients|days|months|years)", sentence, re.IGNORECASE):
        score += 0.4

    # Contains actionable language
    if re.search(
        r"\b(?:should|try|consider|recommend|make sure|key was|tip)\b", sentence, re.IGNORECASE
    ):
        score += 0.3

    # Contains specific entities
    if re.search(r"\b(?:CPT|97\d{3}|Medicare|BCBS|WebPT|PECOS)\b", sentence, re.IGNORECASE):
        score += 0.2

    # Contains contrast/nuance
    if re.search(r"\b(?:however|but|although|careful|be aware)\b", sentence, re.IGNORECASE):
        score += 0.2

    return score


def extractive_summary(
    posts: list[dict],
    max_bullets: int = 5,
) -> list[dict]:
    """Generate extractive summary from posts.

    Each bullet is a selected sentence with mandatory source citation.
    Returns list of {text: str, post_id: str, comment_id: str|None, thread_id: str}.

    ZERO hallucination: every bullet is a direct quote from the source data.
    """
    candidates = []

    for post in posts:
        text = post.get("text_redacted", post.get("text", ""))
        post_id = post.get("post_id", "")
        comment_id = post.get("comment_id")
        thread_id = post.get("thread_id", "")

        sentences = _split_sentences(text)
        for sentence in sentences:
            score = _score_sentence(sentence)
            candidates.append(
                {
                    "sentence": sentence,
                    "score": score,
                    "post_id": post_id,
                    "comment_id": comment_id,
                    "thread_id": thread_id,
                }
            )

    # Sort by score descending
    candidates.sort(key=lambda x: x["score"], reverse=True)

    # Deduplicate similar sentences
    selected = []
    seen_starts = set()
    for c in candidates:
        # Use first 50 chars as dedup key
        key = c["sentence"][:50].lower()
        if key not in seen_starts:
            seen_starts.add(key)
            selected.append(c)
        if len(selected) >= max_bullets:
            break

    # Format as evidence bullets with citations
    bullets = []
    for s in selected:
        citation_parts = [f"thread_id:{s['thread_id']}"]
        if s["comment_id"]:
            citation_parts.append(f"comment_id:{s['comment_id']}")
        else:
            citation_parts.append(f"post_id:{s['post_id']}")
        citation = ", ".join(citation_parts)

        bullets.append(
            {
                "text": f"{s['sentence']} [{citation}]",
                "post_id": s["post_id"],
                "comment_id": s["comment_id"],
                "thread_id": s["thread_id"],
                "score": s["score"],
            }
        )

    return bullets


def format_briefing(
    title: str,
    bullets: list[dict],
) -> str:
    """Format evidence bullets as a markdown briefing."""
    lines = [f"## {title}", ""]
    for b in bullets:
        lines.append(f"- {b['text']}")
    lines.append("")
    return "\n".join(lines)


def validate_citations(summary_text: str) -> bool:
    """Validate that every bullet in a summary has source citations.

    Returns True if all bullets have citations, False otherwise.
    """
    lines = summary_text.strip().split("\n")
    bullet_lines = [ln for ln in lines if ln.strip().startswith("- ")]

    if not bullet_lines:
        return True  # No bullets to validate

    for line in bullet_lines:
        # Must contain [thread_id:..., post_id:...] or [thread_id:..., comment_id:...]
        if not re.search(r"\[thread_id:[^]]+\]", line):
            return False

    return True
