"""Tests for enrichment: taxonomy tagging, metrics, entity extraction."""

import pandas as pd

from pt_insights_os.enrich.entities import (
    classify_business_stage,
    classify_intent,
    classify_setting,
    extract_entities,
)
from pt_insights_os.enrich.metrics import compute_post_scores, compute_thread_scores
from pt_insights_os.taxonomy.rules import match_rules
from pt_insights_os.taxonomy.tagger import build_tag_registry, tag_text


class TestTaxonomy:
    def test_tag_registry_loads(self):
        registry = build_tag_registry()
        assert len(registry) > 50  # Should have many tags

    def test_tag_has_hierarchy(self):
        registry = build_tag_registry()
        for tag_name, info in registry.items():
            assert "l1_domain" in info
            assert "l2_subdomain" in info
            assert "l3_tag" in info
            assert info["l1_domain"]
            assert info["l2_subdomain"]


class TestRuleMatching:
    def test_matches_cash_based(self):
        matches = match_rules("I'm transitioning to a cash-based practice model")
        tag_names = [m[0] for m in matches]
        assert "cash_based_transition" in tag_names

    def test_matches_burnout(self):
        matches = match_rules("I'm experiencing burnout from seeing 30 patients a day")
        tag_names = [m[0] for m in matches]
        assert "workload_stress" in tag_names

    def test_matches_cpt_codes(self):
        matches = match_rules("97110 pays less every year")
        tag_names = [m[0] for m in matches]
        assert "cpt_codes" in tag_names

    def test_matches_emr(self):
        matches = match_rules("We use WebPT for documentation")
        tag_names = [m[0] for m in matches]
        assert "webpt" in tag_names

    def test_no_matches_on_empty(self):
        matches = match_rules("")
        assert len(matches) == 0

    def test_matches_hiring(self):
        matches = match_rules("We are hiring a new PT for our outpatient clinic")
        tag_names = [m[0] for m in matches]
        assert "recruitment" in tag_names


class TestHybridTagger:
    def test_tag_text_returns_assignments(self):
        assignments = tag_text("We're transitioning to cash-based PT and use WebPT for our EMR")
        assert len(assignments) > 0
        for a in assignments:
            assert "tag_id" in a
            assert "tag_name" in a
            assert "confidence" in a
            assert "source" in a
            assert a["source"] in ("rule", "embedding", "llm")

    def test_rule_matches_have_confidence_1(self):
        assignments = tag_text("Call about billing Medicare claim denials")
        rule_assignments = [a for a in assignments if a["source"] == "rule"]
        for a in rule_assignments:
            assert a["confidence"] == 1.0


class TestEntityExtraction:
    def test_extract_insurer(self):
        entities = extract_entities("UnitedHealthcare denied our claim", "p1")
        types = [e["entity_type"] for e in entities]
        assert "INSURER" in types

    def test_extract_emr(self):
        entities = extract_entities("We switched to WebPT last month", "p1")
        types = [e["entity_type"] for e in entities]
        assert "EMR" in types

    def test_extract_cpt(self):
        entities = extract_entities("97110 and 97140 are our most used codes", "p1")
        types = [e["entity_type"] for e in entities]
        assert "CPT_CODE" in types

    def test_extract_credential(self):
        entities = extract_entities("She has her OCS and DPT", "p1")
        types = [e["entity_type"] for e in entities]
        assert "CREDENTIAL" in types

    def test_no_entities_in_clean_text(self):
        entities = extract_entities("The weather is nice today", "p1")
        assert len(entities) == 0


class TestClassifiers:
    def test_intent_question(self):
        assert classify_intent("Has anyone tried dry needling? How does it work?") == "question"

    def test_intent_advice(self):
        assert classify_intent("You should consider adding telehealth") == "advice"

    def test_intent_experience(self):
        assert classify_intent("I made the switch last year and it was great") == "experience_share"

    def test_business_stage_startup(self):
        assert classify_business_stage("I'm planning to start my own practice") == "startup"

    def test_business_stage_growth(self):
        assert classify_business_stage("We're expanding to a second location") == "growth"

    def test_setting_outpatient(self):
        assert classify_setting("I work in an outpatient clinic") == "outpatient"

    def test_setting_home_health(self):
        assert classify_setting("I do home health visits") == "home_health"


class TestMetrics:
    def test_compute_post_scores(self):
        df = pd.DataFrame(
            {
                "post_id": ["p1", "p2"],
                "text_redacted": [
                    "You should consider trying cash pay. It really helped us grow revenue by 40%.",
                    "Just frustrated with burnout and overwhelming patient loads.",
                ],
                "reactions": [10, 5],
            }
        )
        result = compute_post_scores(df)
        assert "actionable_density" in result.columns
        assert "burnout_signal_score" in result.columns
        assert "owner_relevance_score" in result.columns
        assert result.iloc[1]["burnout_signal_score"] == 1.0

    def test_compute_thread_scores(self):
        posts_df = pd.DataFrame(
            {
                "post_id": ["p1", "p2"],
                "thread_id": ["t1", "t1"],
                "text_redacted": ["Great advice here", "However, be careful with this approach"],
                "reactions": [10, 5],
                "actionable_density": [0.5, 0.3],
                "owner_relevance_score": [1.0, 0.0],
                "burnout_signal_score": [0.0, 0.0],
            }
        )
        threads_df = pd.DataFrame(
            {
                "thread_id": ["t1"],
                "post_count": [2],
            }
        )
        result = compute_thread_scores(posts_df, threads_df)
        assert "thread_quality_score" in result.columns
        assert "disagreement_score" in result.columns
        assert result.iloc[0]["disagreement_score"] > 0  # "however" triggers disagreement
