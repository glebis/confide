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
SESSIONS_EN = DATA / "sessions-en"

RESULTS = ROOT / "results"

CACHE = ROOT / "caches" / "detector-cache"
RUNS = ROOT / "caches" / "runs"

DOCS = ROOT / "docs"

# anonymize.py lives in the session-anonymizer skill, imported via sys.path.
SKILLS = ROOT / "skills"
ANONYMIZER_SCRIPTS = SKILLS / "session-anonymizer" / "scripts"

# Canonical gold files.
GOLD = {
    "ru":      SESSIONS_RU / "pii-eval-ru.jsonl",
    "ru-adv":  SESSIONS_RU / "pii-adversarial-ru.jsonl",
    "en":      SESSIONS_EN / "pii-eval.jsonl",
    "en-real": SESSIONS_EN / "pii-eval-ai4privacy.jsonl",
}
