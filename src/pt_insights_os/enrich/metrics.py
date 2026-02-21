"""Compute derived thread/post scores."""

import re

import pandas as pd


def _word_count(text: str) -> int:
    return len(text.split()) if text else 0


def _sentence_count(text: str) -> int:
    if not text:
        return 0
    return max(1, len(re.split(r"[.!?]+", text.strip())))


def _has_question(text: str) -> bool:
    return "?" in text if text else False


def _has_actionable_language(text: str) -> bool:
    patterns = [
        r"\bshould\b", r"\btry\b", r"\bconsider\b", r"\brecommend\b",
        r"\bstep\s+\d\b", r"\bfirst\b.*\bthen\b", r"\bhow to\b",
        r"\bmake sure\b", r"\bdon't forget\b", r"\btip[s:]?\b",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns) if text else False


def _has_burnout_signal(text: str) -> bool:
    patterns = [
        r"\bburnout\b", r"\bexhaust\w*\b", r"\boverwhelm\w*\b",
        r"\bstress\w*\b", r"\bquit(?:ting)?\b", r"\bunsustainable\b",
        r"\bcan't take\b", r"\btoo many patients\b", r"\bdocument(?:ing)?\s+until\b",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns) if text else False


def _has_owner_relevance(text: str) -> bool:
    patterns = [
        r"\bpractice own\w*\b", r"\bclinic own\w*\b", r"\bmy (?:practice|clinic|business)\b",
        r"\bstarting a (?:practice|clinic)\b", r"\bowner\b", r"\bentrepreneur\b",
        r"\brevenue\b", r"\bprofit\b", r"\bcash[- ]?(?:based|pay)\b",
        r"\bhir(?:e|ing)\b", r"\bscal(?:e|ing)\b", r"\bmulti[- ]?location\b",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns) if text else False


def compute_post_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Add score columns to posts DataFrame."""
    df = df.copy()
    text_col = "text_redacted" if "text_redacted" in df.columns else "text"

    # Actionable density: fraction of sentences with actionable language
    def actionable_density(text):
        if not text:
            return 0.0
        sentences = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
        if not sentences:
            return 0.0
        actionable = sum(1 for s in sentences if _has_actionable_language(s))
        return round(actionable / len(sentences), 3)

    df["actionable_density"] = df[text_col].apply(actionable_density)
    df["burnout_signal_score"] = df[text_col].apply(
        lambda t: 1.0 if _has_burnout_signal(t) else 0.0
    )
    df["owner_relevance_score"] = df[text_col].apply(
        lambda t: 1.0 if _has_owner_relevance(t) else 0.0
    )

    return df


def compute_thread_scores(posts_df: pd.DataFrame, threads_df: pd.DataFrame) -> pd.DataFrame:
    """Compute thread-level scores from posts."""
    threads_df = threads_df.copy()
    text_col = "text_redacted" if "text_redacted" in posts_df.columns else "text"

    for thread_id in threads_df["thread_id"].unique():
        thread_posts = posts_df[posts_df["thread_id"] == thread_id]
        mask = threads_df["thread_id"] == thread_id

        if thread_posts.empty:
            continue

        # Thread quality = f(post_count, reactions, reply_depth, word_count)
        avg_words = thread_posts[text_col].apply(_word_count).mean()
        total_reactions = thread_posts["reactions"].sum() if "reactions" in thread_posts.columns else 0
        post_count = len(thread_posts)
        quality = min(1.0, round(
            (min(avg_words, 100) / 100 * 0.3) +
            (min(total_reactions, 50) / 50 * 0.3) +
            (min(post_count, 10) / 10 * 0.4),
            3
        ))
        threads_df.loc[mask, "thread_quality_score"] = quality

        # Novelty: presence of unique/uncommon words (simplified)
        all_text = " ".join(thread_posts[text_col].fillna(""))
        unique_words = set(all_text.lower().split())
        novelty = min(1.0, round(len(unique_words) / max(100, len(all_text.split())) * 0.5, 3))
        threads_df.loc[mask, "novelty_score"] = novelty

        # Disagreement: presence of contrasting language
        disagree_patterns = [r"\bbut\b", r"\bhowever\b", r"\bdisagree\b", r"\bcareful\b",
                           r"\bon the other hand\b", r"\bactually\b", r"\bnot necessarily\b"]
        disagree_count = sum(
            1 for text in thread_posts[text_col].fillna("")
            for p in disagree_patterns
            if re.search(p, text, re.IGNORECASE)
        )
        disagreement = min(1.0, round(disagree_count / max(1, post_count) * 0.5, 3))
        threads_df.loc[mask, "disagreement_score"] = disagreement

        # Aggregate post-level scores
        if "actionable_density" in posts_df.columns:
            threads_df.loc[mask, "actionable_density"] = round(
                thread_posts["actionable_density"].mean(), 3
            )
        if "owner_relevance_score" in posts_df.columns:
            threads_df.loc[mask, "owner_relevance_score"] = round(
                thread_posts["owner_relevance_score"].max(), 3
            )
        if "burnout_signal_score" in posts_df.columns:
            threads_df.loc[mask, "burnout_signal_score"] = round(
                thread_posts["burnout_signal_score"].max(), 3
            )

    return threads_df
