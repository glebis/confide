import json
import os
import sys
import urllib.request
import pytest

from confide_eval import paths
from confide_eval.detectors import run_llm_detector
from confide_eval.scoring import score_llm_experiment

if os.fspath(paths.ANONYMIZER_SCRIPTS) not in sys.path:
    sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))

import anonymize  # noqa: E402


def test_prompt_template_replaces_text_without_formatting_json_braces():
    prompt = 'Return [{"text":"exact","type":"PERSON"}]\nText:\n{text}'

    rendered = anonymize._render_llm_prompt("Аня живет в Москве", prompt)

    assert '[{"text":"exact","type":"PERSON"}]' in rendered
    assert "Аня живет в Москве" in rendered


def test_prompt_template_without_placeholder_appends_text():
    rendered = anonymize._render_llm_prompt("hello", "Return JSON.")

    assert rendered == "Return JSON.\n\nText: hello"


def test_extract_json_array_uses_first_valid_array_with_trailing_data():
    output = '```json\n[{"text":"Анна","type":"PERSON"}]\n```\n[{"text":"Москва","type":"LOCATION"}]'

    entities = anonymize._extract_json_array(output)

    assert entities == [{"text": "Анна", "type": "PERSON"}]


def test_iter_text_chunks_prefers_line_boundary_and_overlaps():
    text = "first line has pii\nsecond line has more pii\nthird line"

    chunks = list(anonymize.iter_text_chunks(text, chunk_chars=32, overlap=5))

    assert chunks[0] == (0, "first line has pii\n")
    assert chunks[1][0] == len("first line has pii\n") - 5
    assert chunks[-1][1].endswith("third line")


def test_run_ollama_chunked_offsets_relative_spans(monkeypatch):
    calls = []

    def fake_run_ollama(chunk, model="", prompt_template=None):
        calls.append(chunk)
        idx = chunk.find("PII")
        if idx == -1:
            return []
        return [anonymize.Span(
            start=idx,
            end=idx + 3,
            text="PII",
            label="PERSON",
            source="ollama",
        )]

    monkeypatch.setattr(anonymize, "run_ollama", fake_run_ollama)

    spans = anonymize.run_ollama_chunked(
        "aaaa PII\nbbbbbbbbbbbbbbbb PII",
        "gemma3:latest",
        chunk_chars=16,
        overlap=4,
    )

    assert [s.start for s in spans] == [5, 26]
    assert [s.text for s in spans] == ["PII", "PII"]
    assert len(calls) > 1


def test_run_ollama_ollama_payload_disables_thinking(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return b'{"message":{"content":"[]"}}'

    def fake_urlopen(req, timeout):
        captured["payload"] = json.loads(req.data.decode())
        return FakeResponse()

    monkeypatch.delenv("LLM_API", raising=False)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    spans = anonymize.run_ollama(
        "hello",
        model="gemma4:12b-mlx",
        prompt_template="Return [] for {text}",
    )

    assert spans == []
    assert captured["payload"]["think"] is False


def test_default_stack_uses_ru_and_en_detector_layers():
    assert score_llm_experiment.default_stack("ru", "local-gemma3-4b-p1") == [
        "natasha",
        "regex",
        "local-gemma3-4b-p1",
    ]
    assert score_llm_experiment.default_stack("ru-real", "local-gemma3-4b-p1") == [
        "natasha",
        "regex",
        "local-gemma3-4b-p1",
    ]
    assert score_llm_experiment.default_stack("en", "local-gemma3-4b-p1") == [
        "opf",
        "regex",
        "local-gemma3-4b-p1",
    ]


def test_remote_base_url_rejected_unless_explicitly_allowed():
    assert run_llm_detector._is_local_base("http://localhost:11434")
    assert run_llm_detector._is_local_base("http://127.0.0.1:8080")
    assert not run_llm_detector._is_local_base("https://api.example.com")


def test_read_cache_rows_for_resume_validates_jsonl(tmp_path):
    cache = tmp_path / "detector.jsonl"
    cache.write_text(
        '{"doc_id":"d1","spans":[{"start":0,"end":3,"type":"PERSON"}]}\n',
        encoding="utf-8",
    )

    rows = run_llm_detector._read_cache_rows(os.fspath(cache))

    assert rows["d1"]["spans"][0]["type"] == "PERSON"

    cache.write_text('{"spans":[]}\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="has no doc_id"):
        run_llm_detector._read_cache_rows(os.fspath(cache))


def test_write_cache_checkpoint_preserves_completed_doc_order(tmp_path):
    cache = tmp_path / "detector.jsonl"
    docs = [{"doc_id": "d1"}, {"doc_id": "d2"}, {"doc_id": "d3"}]
    rows = {
        "d3": {"doc_id": "d3", "spans": []},
        "d1": {"doc_id": "d1", "spans": [{"start": 0, "end": 1, "type": "ID"}]},
    }

    run_llm_detector._write_cache_checkpoint(os.fspath(cache), docs, rows)

    written = [json.loads(line) for line in cache.read_text(encoding="utf-8").splitlines()]
    assert [row["doc_id"] for row in written] == ["d1", "d3"]
    assert run_llm_detector._read_cache_rows(os.fspath(cache))["d3"]["spans"] == []
