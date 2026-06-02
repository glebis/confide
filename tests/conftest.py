"""Pytest fixtures / path setup for the confide-eval test suite.

`pythonpath = ["src"]` in pyproject.toml makes the `confide_eval` package
importable. We additionally put `src/` on sys.path here so the tests run the
same way whether invoked via `pytest`, `make test`, or `python3 tests/test_x.py`
directly. The session-anonymizer skill (anonymize.py) is added via the package's
own path constants.
"""
import os
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from confide_eval import paths  # noqa: E402

if os.fspath(paths.ANONYMIZER_SCRIPTS) not in sys.path:
    sys.path.insert(0, os.fspath(paths.ANONYMIZER_SCRIPTS))
