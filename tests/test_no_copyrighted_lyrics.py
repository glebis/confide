"""Release guard: no multi-line copyrighted song-lyric excerpt in public docs.

A single attributed line as an epigraph (the cultural reference the project name
plays on) is a defensible fair-use quotation; a multi-line excerpt of a
commercially released song is not redistributable under the repo's MIT/CC-BY
licenses. This guard fails if the removed lyric lines reappear anywhere in the
public-facing docs. (P0 release-review issue #18.)
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = ["README.md", "docs/CONFIDE-README.md"]

# Lyric lines that MUST NOT appear. The kept epigraph (two attributed lines —
# "But in the name of understanding / Our problems should be shared") is a
# deliberate fair-use cultural reference and is allowed; everything else is not.
BANNED_LYRIC_LINES = [
    "throw away the key",
    "sometimes to release it",
    "set our children free",
    "we all get hurt by love",
    "we all have our cross to bear",
]


def _read(path):
    p = os.path.join(ROOT, path)
    return open(p, encoding="utf-8").read().lower() if os.path.exists(p) else ""


def test_no_multiline_lyric_excerpt_in_public_docs():
    offenders = []
    for doc in DOCS:
        text = _read(doc)
        for line in BANNED_LYRIC_LINES:
            if line in text:
                offenders.append(f"{doc}: '{line}'")
    assert not offenders, "copyrighted lyric lines still present (fair use = one short attributed line only): " + "; ".join(offenders)
