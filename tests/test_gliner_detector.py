"""GLiNER detector layer: label mapping, post-processing, and registry wiring.

The mapping/trim/dedupe tests run without the model (they exercise the pure
post-processing path by monkeypatching the lazy loader); the live smoke test
is skipped unless the `gliner` package and downloaded weights are available.
"""
import pytest

from confide_eval.detectors import run_detectors
from confide_eval.detectors.run_llm_detector import RESERVED_DETECTORS
from confide_eval.scoring.score_bench import CANON


class _FakeGliner:
    def __init__(self, entities):
        self._entities = entities
        self.calls = []

    def predict_entities(self, text, labels, threshold):
        self.calls.append((text, tuple(labels), threshold))
        return [dict(e) for e in self._entities]


def _with_fake_model(monkeypatch, entities):
    fake = _FakeGliner(entities)
    monkeypatch.setattr(run_detectors, "_GLINER", fake)
    return fake


def test_gliner_is_reserved_detector_name():
    assert "gliner" in RESERVED_DETECTORS


def test_gliner_labels_all_map_to_canonical_types():
    for raw in run_detectors._GLINER_LABELS.values():
        assert CANON.get(raw) is not None, f"unmapped raw label {raw!r}"


def test_gliner_spans_mapped_trimmed_and_sourced(monkeypatch):
    text = "Call  Anna Petrova , ok?"
    _with_fake_model(monkeypatch, [
        {"label": "person", "start": 5, "end": 20, "score": 0.99},
    ])
    spans = run_detectors.run_gliner(text)
    assert spans == [
        {"start": 6, "end": 18, "type": "PERSON", "source": "gliner"}
    ]
    assert text[6:18] == "Anna Petrova"


def test_gliner_unknown_label_dropped(monkeypatch):
    _with_fake_model(monkeypatch, [
        {"label": "favourite colour", "start": 0, "end": 4, "score": 0.9},
    ])
    assert run_detectors.run_gliner("blue and more") == []


def test_gliner_window_overlap_duplicates_deduped(monkeypatch):
    # the same entity reported from two overlapping windows must appear once
    text = "x" * 1300 + " Anna"
    fake = _FakeGliner([{"label": "person", "start": 0, "end": 4, "score": 0.9}])

    def predict(chunk, labels, threshold):
        # report 'Anna' relative to any window that contains it
        idx = chunk.find("Anna")
        if idx < 0:
            return []
        return [{"label": "person", "start": idx, "end": idx + 4, "score": 0.9}]

    fake.predict_entities = lambda chunk, labels, threshold: predict(chunk, labels, threshold)
    monkeypatch.setattr(run_detectors, "_GLINER", fake)
    spans = run_detectors.run_gliner(text, window=1200, overlap=150)
    assert len(spans) == 1
    assert text[spans[0]["start"]:spans[0]["end"]] == "Anna"


def test_gliner_id_phrasings_map_to_id():
    for phrasing in ("social security number", "passport number",
                     "account number", "id number"):
        assert run_detectors._GLINER_LABELS[phrasing] == "ID"


@pytest.mark.skipif(
    not pytest.importorskip("gliner", reason="gliner not installed"),
    reason="gliner not installed",
)
def test_gliner_live_smoke_ru_en():
    try:
        model = run_detectors._gliner_model()
    except Exception as e:  # no weights / offline
        pytest.skip(f"gliner weights unavailable: {e}")
    ru = "Меня зовут Анна Смирнова, мой телефон +7 916 123-45-67."
    spans = run_detectors.run_gliner(ru)
    types = {s["type"] for s in spans}
    assert "PERSON" in types
    assert "PHONE" in types
