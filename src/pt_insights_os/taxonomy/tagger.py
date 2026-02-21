"""Hybrid tagger: rules → embedding similarity → optional LLM."""

import uuid
from pathlib import Path

import yaml

from pt_insights_os.config import ENABLE_LLM_TAGGER
from pt_insights_os.logging_config import setup_logging
from pt_insights_os.taxonomy.rules import match_rules

logger = setup_logging()

TAXONOMY_PATH = Path(__file__).parent / "taxonomy.yaml"


def load_taxonomy() -> dict:
    """Load the taxonomy YAML."""
    with open(TAXONOMY_PATH) as f:
        return yaml.safe_load(f)


def build_tag_registry() -> dict[str, dict]:
    """Build a flat registry of all tags with their L1/L2/L3 info."""
    taxonomy = load_taxonomy()
    registry = {}
    for domain_id, domain in taxonomy["domains"].items():
        for subdomain_id, subdomain in domain["subdomains"].items():
            for tag in subdomain["tags"]:
                tag_id = f"tag_{uuid.uuid5(uuid.NAMESPACE_DNS, f'{domain_id}.{subdomain_id}.{tag}').hex[:12]}"
                registry[tag] = {
                    "tag_id": tag_id,
                    "l1_domain": domain["label"],
                    "l2_subdomain": subdomain["label"],
                    "l3_tag": tag,
                }
    return registry


# Global tag registry
_TAG_REGISTRY = None


def get_tag_registry() -> dict[str, dict]:
    global _TAG_REGISTRY
    if _TAG_REGISTRY is None:
        _TAG_REGISTRY = build_tag_registry()
    return _TAG_REGISTRY


def _embedding_tag(text: str, tag_registry: dict) -> list[tuple[str, float]]:
    """Embedding similarity backstop — uses TF-IDF cosine as lightweight fallback."""
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        return []

    # Build tag descriptions from L1 + L2 + L3 names
    tag_names = list(tag_registry.keys())
    tag_texts = [
        f"{info['l1_domain']} {info['l2_subdomain']} {tag.replace('_', ' ')}"
        for tag, info in tag_registry.items()
    ]

    all_texts = [text] + tag_texts
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf = vectorizer.fit_transform(all_texts)
    except ValueError:
        return []

    similarities = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    # Return tags above threshold
    threshold = 0.15
    results = []
    for i, sim in enumerate(similarities):
        if sim >= threshold:
            results.append((tag_names[i], round(float(sim), 3)))

    # Sort by similarity descending, limit to top 5
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:5]


def tag_text(text: str) -> list[dict]:
    """Tag text using hybrid approach: rules first, then embedding similarity."""
    if not text or not text.strip():
        return []

    tag_registry = get_tag_registry()
    assignments = []
    seen_tags = set()

    # 1. Rule-based matching (deterministic, highest confidence)
    rule_matches = match_rules(text)
    for tag_name, confidence in rule_matches:
        if tag_name in tag_registry and tag_name not in seen_tags:
            info = tag_registry[tag_name]
            assignments.append({
                "assignment_id": f"ta_{uuid.uuid4().hex[:12]}",
                "tag_id": info["tag_id"],
                "tag_name": tag_name,
                "l1_domain": info["l1_domain"],
                "l2_subdomain": info["l2_subdomain"],
                "l3_tag": info["l3_tag"],
                "confidence": confidence,
                "source": "rule",
            })
            seen_tags.add(tag_name)

    # 2. Embedding similarity backstop (only if rules found < 2 tags)
    if len(assignments) < 2:
        embed_matches = _embedding_tag(text, tag_registry)
        for tag_name, confidence in embed_matches:
            if tag_name not in seen_tags:
                info = tag_registry[tag_name]
                assignments.append({
                    "assignment_id": f"ta_{uuid.uuid4().hex[:12]}",
                    "tag_id": info["tag_id"],
                    "tag_name": tag_name,
                    "l1_domain": info["l1_domain"],
                    "l2_subdomain": info["l2_subdomain"],
                    "l3_tag": info["l3_tag"],
                    "confidence": confidence,
                    "source": "embedding",
                })
                seen_tags.add(tag_name)

    # 3. Optional LLM classifier (OFF by default)
    if ENABLE_LLM_TAGGER:
        logger.info("LLM tagger is enabled but not implemented — skipping")

    return assignments
