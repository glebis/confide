"""Root-anchored path constants for the confide-eval package.

Every script resolves its data / cache / result / doc locations through these
constants instead of computing paths relative to its own file. This decouples
"where a script lives" from "where the data lives", so the physical package
layout can change without breaking any I/O path. See docs/REPRODUCIBILITY.md.
"""
from pathlib import Path

# This file is src/confide_eval/paths.py, so parents[2] is the repo root.
ROOT = Path(__file__).resolve().parents[2]

DATA = ROOT / "data"
SESSIONS_RU = DATA / "sessions-ru"
SESSIONS_RU_REAL = DATA / "sessions-ru-real"
SESSIONS_EN = DATA / "sessions-en"

RESULTS = ROOT / "results"

CACHE = ROOT / "caches" / "detector-cache"
RUNS = ROOT / "caches" / "runs"

DOCS = ROOT / "docs"

# anonymize.py lives in the session-anonymizer skill, imported via sys.path.
SKILLS = ROOT / "skills"
ANONYMIZER_SCRIPTS = SKILLS / "session-anonymizer" / "scripts"

# Canonical gold files.
#
# EN-real (ai4privacy) is special: the committed file ships span offsets +
# per-doc sha256 ONLY — the source `text` is NOT redistributed (ai4privacy's
# license restricts redistribution). A runnable, text-bearing copy is fetched
# on demand by `python -m confide_eval.data.fetch_ai4privacy`, which writes the
# gitignored `*.local.jsonl` below. en_real_gold() prefers the local file when
# present and falls back to the stripped (text-less) committed file otherwise.
GOLD = {
    "ru":      SESSIONS_RU / "pii-eval-ru.jsonl",
    "ru-adv":  SESSIONS_RU / "pii-adversarial-ru.jsonl",
    "en":      SESSIONS_EN / "pii-eval.jsonl",
    "en-real": SESSIONS_EN / "pii-eval-ai4privacy.jsonl",
    # RU-real: real-TEXT Russian de-id slice derived from the JayGuard NER
    # benchmark (Apache-2.0; redistributed WITH attribution — text IS committed).
    # Real conversational RU, NOT therapy; machine-derived gold, not adjudicated.
    "ru-real": SESSIONS_RU_REAL / "jayguard-ru.jsonl",
}

# Stripped (committed, text-less) and local (fetched, text-bearing) EN-real gold.
EN_REAL_STRIPPED = SESSIONS_EN / "pii-eval-ai4privacy.jsonl"
EN_REAL_LOCAL = SESSIONS_EN / "pii-eval-ai4privacy.local.jsonl"


def en_real_gold():
    """Resolve the EN-real gold path: the fetched `.local.jsonl` (text present)
    if it exists, else the stripped committed file (no source text)."""
    return EN_REAL_LOCAL if EN_REAL_LOCAL.exists() else EN_REAL_STRIPPED


def en_real_text_present():
    """True iff the runnable, text-bearing EN-real gold has been fetched."""
    return EN_REAL_LOCAL.exists()
