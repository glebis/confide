"""TDD tests for confide_eval.scoring.regulatory — the pure metric cores.

These cover the logic that is easy to get subtly wrong (HIPAA coverage rule,
the residual-risk tier ordering, worst-case-leak statistics, inference rate).
Data-loading/orchestration is exercised by the smoke test at the end.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from confide_eval.scoring import regulatory as reg


# ---------------------------------------------------------------- HIPAA
def test_hipaa_category_passes_when_no_mentions_leak():
    per_type = {"PERSON": {"support": 5, "fn": 0}}
    out = reg.hipaa_coverage(per_type)
    assert out["categories"]["PERSON"]["passed"] is True
    assert out["applicable"] == 1
    assert out["passed"] == 1
    assert out["removed_frac"] == 1.0


def test_hipaa_category_fails_when_a_mention_leaks():
    per_type = {"DATE": {"support": 23, "fn": 2}}
    out = reg.hipaa_coverage(per_type)
    assert out["categories"]["DATE"]["passed"] is False
    assert out["applicable"] == 1
    assert out["passed"] == 0
    assert out["removed_frac"] == 0.0


def test_hipaa_age_is_marked_na_not_counted():
    # Only ages >89 are HIPAA identifiers and the gold carries no age value.
    per_type = {"AGE": {"support": 24, "fn": 3}, "PERSON": {"support": 2, "fn": 0}}
    out = reg.hipaa_coverage(per_type)
    assert "AGE" in out["na"]
    assert "AGE" not in out["categories"]
    assert out["applicable"] == 1  # only PERSON is applicable


def test_hipaa_medication_profession_are_special_category_not_hipaa():
    per_type = {"MEDICATION": {"support": 4, "fn": 1}, "PROFESSION": {"support": 3, "fn": 0}}
    out = reg.hipaa_coverage(per_type)
    assert set(out["special_category"]) == {"MEDICATION", "PROFESSION"}
    assert "MEDICATION" not in out["categories"]
    assert out["applicable"] == 0


def test_hipaa_zero_support_category_is_not_applicable():
    per_type = {"PHONE": {"support": 0, "fn": 0}, "EMAIL": {"support": 2, "fn": 0}}
    out = reg.hipaa_coverage(per_type)
    assert "PHONE" not in out["categories"]
    assert out["applicable"] == 1


# ------------------------------------------------------- residual-risk tier
def test_tier_red_when_any_direct_identifier_leaks():
    assert reg.residual_risk_tier(direct_residual=1, special_residual=0,
                                  inference_rate=0.0, linkability_above_base=False) == "RED"


def test_tier_amber_on_special_category_residual():
    assert reg.residual_risk_tier(0, special_residual=2, inference_rate=0.0,
                                  linkability_above_base=False) == "AMBER"


def test_tier_amber_on_nonzero_inference():
    assert reg.residual_risk_tier(0, 0, inference_rate=0.4, linkability_above_base=False) == "AMBER"


def test_tier_amber_on_linkability_above_base():
    assert reg.residual_risk_tier(0, 0, 0.0, linkability_above_base=True) == "AMBER"


def test_tier_green_when_all_clear():
    assert reg.residual_risk_tier(0, 0, 0.0, False) == "GREEN"


# ------------------------------------------------------------- percentile
def test_percentile_endpoints_and_midpoint():
    assert reg.percentile([0.0, 1.0], 0) == 0.0
    assert reg.percentile([0.0, 1.0], 100) == 1.0
    assert reg.percentile([0.0, 10.0], 50) == 5.0


def test_percentile_empty_is_zero():
    assert reg.percentile([], 50) == 0.0


# ----------------------------------------------------------- worst-case leak
def test_worst_case_leak_stats_and_rate():
    per_doc = [
        {"doc_id": "a", "leaked": 0, "gold": 4, "chars": 1000},
        {"doc_id": "b", "leaked": 2, "gold": 2, "chars": 1000},
    ]
    out = reg.worst_case_leak(per_doc)
    assert out["min_recall"] == 0.0          # doc b leaked everything
    assert out["mean_recall"] == 0.5
    assert out["total_leaked"] == 2
    assert out["worst_doc"] == "b"
    # 2 leaked mentions over 2000 chars -> 10 per 10k chars
    assert out["leaked_per_10k_chars"] == 10.0


def test_worst_case_leak_empty():
    out = reg.worst_case_leak([])
    assert out["total_leaked"] == 0
    assert out["min_recall"] == 1.0          # nothing to leak == fully protected


# ----------------------------------------------- in-scope vs out-of-scope
def test_spelled_out_digit_phone_words_only():
    assert reg.is_spelled_out_digit("PHONE", "плюс семь, девять-один-шесть") is True


def test_spelled_out_digit_phone_with_digits_is_in_scope():
    assert reg.is_spelled_out_digit("PHONE", "+7 916 555-21-43") is False


def test_spelled_out_digit_only_for_phone_and_id():
    assert reg.is_spelled_out_digit("PERSON", "Вера") is False  # a name is never "spelled-out digits"


def test_spelled_out_digit_id_words():
    assert reg.is_spelled_out_digit("ID", "семь-семь-два-два") is True


def test_split_direct_residual_classifies_entities():
    leaked = [
        {"entity_id": "a-phone-spelled", "leaked": [{"type": "PHONE", "text": "плюс семь девять"}]},
        {"entity_id": "d-roman", "leaked": [{"type": "PERSON", "text": "Роман"}]},
        # mixed: one in-scope leak makes the whole entity in-scope
        {"entity_id": "mixed", "leaked": [{"type": "ID", "text": "семь два"}, {"type": "PERSON", "text": "X"}]},
    ]
    out = reg.split_direct_residual(leaked)
    assert out["out_of_scope"] == 1
    assert out["in_scope"] == 2
    assert out["out_of_scope_ids"] == ["a-phone-spelled"]


# --------------------------------------------------------------- inference
def test_inference_summary_aggregates_clients():
    recon = {"B_inference_attack": {
        "a": {"n_recovered": 2, "n_tested": 5},
        "b": {"n_recovered": 0, "n_tested": 5},
    }}
    out = reg.inference_summary(recon)
    assert out["n_recovered"] == 2
    assert out["n_tested"] == 10
    assert out["rate"] == 0.2
    assert out["by_client"]["a"] == 0.4


# --------------------------------------------------------------- smoke test
def test_compute_ru_returns_expected_shape():
    out = reg.compute("ru")
    assert set(out).issuperset({"dataset", "wp29", "hipaa", "tier", "worst_case"})
    assert out["tier"]["tier"] in {"RED", "AMBER", "GREEN"}
    json.dumps(out)  # must be JSON-serializable
