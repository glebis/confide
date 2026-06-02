#!/usr/bin/env python3
"""Unit tests for the YAML frontmatter direct-identifier recognizer (T8 leak fix).

The de-identification stack used to leak the cleartext `client_id` (a first name,
often Latin/lowercase) in the leading YAML block, which made cross-session
linkability a trivial exact-string match (AUC 1.0). `run_frontmatter` /
`run_regex` now mask the VALUE of identifying keys inside the frontmatter while
leaving non-name fields and single-letter speaker codes intact.

Run: pytest tests/test_frontmatter.py   (exit 0 = pass)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))
from confide_eval import paths

sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))
import anonymize as a


FM = (
    "---\n"
    "client_id: {cid}\n"
    "session_no: 1\n"
    "date: 15.01.2026\n"
    "modality: CBT\n"
    'therapist: "Т"\n'
    'client: "К"\n'
    "---\n\n"
    "# Сессия 1\n"
)


def _regex_spans(text):
    return a.run_regex(text)


def _masked_values(text, label=None):
    """Set of exact substrings masked by run_regex (optionally filtered by label)."""
    return {s.text for s in _regex_spans(text) if label is None or s.label == label}


def test_masks_cyrillic_and_latin_client_id():
    # marina (already covered in old gold) AND alina (the c–f gold gap) must mask.
    for cid in ("marina", "alina", "roman", "vera", "timur"):
        text = FM.format(cid=cid)
        masked = _masked_values(text)
        assert cid in masked, f"client_id {cid!r} must be masked, got {masked}"
        # and it must be emitted as an ID (a stable per-client handle)
        ids = _masked_values(text, "ID")
        assert cid in ids, f"client_id {cid!r} must be type ID, got {ids}"
    print("ok masks Cyrillic+Latin client_id as ID")


def test_does_not_mask_non_name_fields():
    text = FM.format(cid="marina")
    masked = _masked_values(text)
    # modality value / date value / session_no value are NOT identifiers
    assert "CBT" not in masked, f"modality value CBT must NOT be masked: {masked}"
    assert "15.01.2026" not in {s.text for s in _regex_spans(text)
                                if s.source == "regex" and s.label == "ID"}, \
        "date must not be masked AS a frontmatter ID"
    print("ok leaves modality/date frontmatter values alone")


def test_does_not_mask_single_letter_speaker_codes():
    text = FM.format(cid="marina")
    masked = _masked_values(text)
    # therapist: "Т" and client: "К" are role tags, not identifiers
    assert "Т" not in masked, f'single-letter "Т" must NOT be masked: {masked}'
    assert "К" not in masked, f'single-letter "К" must NOT be masked: {masked}'
    print("ok leaves single-letter speaker codes Т/К alone")


def test_masks_real_name_in_speaker_key():
    # A real multi-letter name in a therapist/client key IS an identifier.
    text = ("---\n"
            "client_id: marina\n"
            'therapist: "Иванов"\n'
            "name: Marina Volkova\n"
            "---\n\n# x\n")
    masked = _masked_values(text)
    assert "Иванов" in masked, f"real therapist name must be masked: {masked}"
    assert "Marina Volkova" in masked, f"name value must be masked: {masked}"
    print("ok masks a real name in a speaker/name key")


def test_only_leading_block():
    # A `client_id:` appearing in the BODY (not the leading frontmatter) is not
    # touched by the frontmatter recognizer.
    text = "no frontmatter here\nclient_id: marina\n"
    fm = a.run_frontmatter(text)
    assert fm == [], f"non-leading client_id must not be masked by frontmatter: {fm}"
    print("ok only scans the leading frontmatter block")


if __name__ == "__main__":
    test_masks_cyrillic_and_latin_client_id()
    test_does_not_mask_non_name_fields()
    test_does_not_mask_single_letter_speaker_codes()
    test_masks_real_name_in_speaker_key()
    test_only_leading_block()
    print("\nALL FRONTMATTER TESTS PASSED")
