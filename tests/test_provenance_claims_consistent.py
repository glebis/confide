"""Release guard: public provenance/license claims must match what actually ships.

The repo ships a real-text RU slice (data/sessions-ru-real/jayguard-ru.jsonl), so a
blanket "all shipped transcripts are synthetic and fictional" disclaimer is false.
And the synthetic-data license is CC-BY-4.0 per LICENSE, so a "Synthetic data: CC0"
claim contradicts the legal source of truth. (P0 release-review issue #20.)
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _norm(path):
    p = os.path.join(ROOT, path)
    return open(p, encoding="utf-8").read().replace("*", "").lower() if os.path.exists(p) else ""


def test_no_blanket_all_synthetic_claim_while_real_text_ships():
    ships_real = os.path.exists(os.path.join(ROOT, "data/sessions-ru-real/jayguard-ru.jsonl"))
    disc = _norm("DISCLAIMER.md")
    if ships_real:
        assert "all shipped transcripts are synthetic and fictional" not in disc, (
            "DISCLAIMER claims all-synthetic while a real-text slice (JayGuard) ships")


def test_synthetic_data_license_is_cc_by_not_cc0():
    # LICENSE declares CC-BY-4.0 for synthetic data; docs must not claim CC0.
    assert "synthetic data: cc0" not in _norm("docs/CONFIDE-README.md"), (
        "CONFIDE-README claims CC0 but LICENSE declares CC-BY-4.0 for synthetic data")
