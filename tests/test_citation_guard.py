"""Citation guard tests — every summary bullet MUST have source IDs."""

import pytest

from pt_insights_os.enrich.summarize import (
    extractive_summary,
    format_briefing,
    validate_citations,
)


SAMPLE_POSTS = [
    {
        "post_id": "post_001",
        "thread_id": "thread_001",
        "comment_id": None,
        "text_redacted": "Has anyone transitioned from insurance-based to cash-based PT? "
        "I'm considering making the switch for my clinic.",
    },
    {
        "post_id": "post_002",
        "thread_id": "thread_001",
        "comment_id": "comment_001",
        "text_redacted": "I made the switch 2 years ago. Best decision ever. "
        "Revenue went up 40% and I dropped from 35 patients/day to 12.",
    },
    {
        "post_id": "post_003",
        "thread_id": "thread_001",
        "comment_id": "comment_002",
        "text_redacted": "Be careful with the transition. I lost 60% of my patients initially. "
        "It took 8 months to rebuild. Make sure you have 6 months of runway.",
    },
]


class TestExtractiveSummary:
    def test_returns_bullets(self):
        bullets = extractive_summary(SAMPLE_POSTS)
        assert len(bullets) > 0
        assert len(bullets) <= 5

    def test_bullets_have_source_ids(self):
        bullets = extractive_summary(SAMPLE_POSTS)
        for b in bullets:
            assert "post_id" in b
            assert "thread_id" in b
            assert b["post_id"]
            assert b["thread_id"]

    def test_bullet_text_has_citation(self):
        """Every bullet text must contain [thread_id:..., ...] citation."""
        bullets = extractive_summary(SAMPLE_POSTS)
        for b in bullets:
            assert "[thread_id:" in b["text"], f"Missing citation in: {b['text']}"

    def test_bullets_are_extractive(self):
        """Bullets must be direct quotes from source text."""
        all_source_text = " ".join(p["text_redacted"] for p in SAMPLE_POSTS)
        bullets = extractive_summary(SAMPLE_POSTS)
        for b in bullets:
            # Strip the citation suffix
            text = b["text"].split(" [thread_id:")[0]
            # The sentence should appear in source text
            assert text in all_source_text, f"Non-extractive bullet: {text}"


class TestBriefingFormat:
    def test_format_briefing(self):
        bullets = extractive_summary(SAMPLE_POSTS)
        briefing = format_briefing("Cash-Based Transition", bullets)
        assert "## Cash-Based Transition" in briefing
        assert "- " in briefing

    def test_briefing_validates(self):
        bullets = extractive_summary(SAMPLE_POSTS)
        briefing = format_briefing("Test", bullets)
        assert validate_citations(briefing)


class TestCitationValidation:
    def test_valid_citations(self):
        text = """## Test
- Revenue went up 40%. [thread_id:t1, post_id:p1]
- Be careful with transition. [thread_id:t1, comment_id:c1]
"""
        assert validate_citations(text)

    def test_missing_citations_fails(self):
        text = """## Test
- Revenue went up 40%.
- Be careful with transition.
"""
        assert not validate_citations(text)

    def test_partial_citations_fails(self):
        text = """## Test
- Revenue went up 40%. [thread_id:t1, post_id:p1]
- Be careful with transition.
"""
        assert not validate_citations(text)

    def test_empty_text_passes(self):
        assert validate_citations("")

    def test_no_bullets_passes(self):
        assert validate_citations("## Just a heading\nSome text without bullets.")


class TestCitationGuardIntegration:
    """Integration test: generate briefing → validate ALL bullets have citations."""

    def test_full_pipeline_citation_guard(self):
        bullets = extractive_summary(SAMPLE_POSTS, max_bullets=5)
        briefing = format_briefing("Integration Test", bullets)

        # THE CRITICAL ASSERTION: briefings fail if any bullet lacks source IDs
        assert validate_citations(briefing), (
            f"CITATION GUARD FAILURE: Briefing contains bullets without source IDs:\n{briefing}"
        )

    def test_single_post_has_citation(self):
        bullets = extractive_summary([SAMPLE_POSTS[0]], max_bullets=3)
        briefing = format_briefing("Single Post", bullets)
        assert validate_citations(briefing)
