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
# EN-real (ai4privacy) is special: ai4privacy-derived source text, spans, caches,
# and results are local-only because the license restricts redistribution. Build
# or fetch it on demand under ai4privacy's own license; the generated file is
# gitignored and absent in the public tree.
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

# Local-only, gitignored EN-real gold. The legacy `.local.jsonl` name is accepted
# for existing worktrees, but new local builds use `pii-eval-ai4privacy.jsonl`.
EN_REAL_LOCAL = SESSIONS_EN / "pii-eval-ai4privacy.jsonl"
EN_REAL_LEGACY_LOCAL = SESSIONS_EN / "pii-eval-ai4privacy.local.jsonl"


def en_real_gold():
    """Resolve the local-only EN-real gold path.

    The path may not exist in a public checkout; callers must check
    en_real_text_present() before loading EN-real.
    """
    if EN_REAL_LOCAL.exists():
        return EN_REAL_LOCAL
    if EN_REAL_LEGACY_LOCAL.exists():
        return EN_REAL_LEGACY_LOCAL
    return EN_REAL_LOCAL


def en_real_text_present():
    """True iff runnable, text-bearing EN-real gold exists locally."""
    return EN_REAL_LOCAL.exists() or EN_REAL_LEGACY_LOCAL.exists()
