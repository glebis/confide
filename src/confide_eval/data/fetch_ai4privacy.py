#!/usr/bin/env python3
"""Build the optional local EN-real (ai4privacy) slice.

WHY THIS EXISTS
---------------
The public repository must not distribute ai4privacy-derived source text, gold
spans, detector caches, or result artifacts. This command re-downloads
``ai4privacy/pii-masking-300k`` under that dataset's own license and writes a
LOCAL, text-bearing runnable gold:

    data/sessions-en/pii-eval-ai4privacy.jsonl   (gitignored)

with records ``{text, spans, source}``. score_bench / run_detectors use this
local file only when it exists (see paths.en_real_gold()).

USAGE
-----
    pip install datasets            # one-time, if not already installed
    python -m confide_eval.data.fetch_ai4privacy

If ``datasets`` is not installed or the network is unavailable, the script
prints a clear instruction and exits non-zero WITHOUT touching the repo.

SAMPLING
--------
The local slice is sampled deterministically by ``build_dataset.build_ai4privacy``
(seed 13) from English validation rows of reasonable length. Because this file is
local-only, public ``make check`` skips EN-real unless the local gold exists.
"""
import sys

from confide_eval import paths
from confide_eval.data.build_dataset import build_ai4privacy


def fetch():
    try:
        import datasets  # noqa: F401
    except ImportError:
        print(
            "[fetch] the `datasets` library is required to fetch ai4privacy.\n"
            "        Install it with:  pip install datasets\n"
            "        Then re-run:      python -m confide_eval.data.fetch_ai4privacy"
        )
        return 1

    out_path = paths.EN_REAL_LOCAL
    ok = build_ai4privacy(out_path)
    if ok:
        print("[fetch] OK — EN-real local-only gold is now runnable. "
              "Do not commit the generated file.")
        return 0
    return 1


def main():
    sys.exit(fetch())


if __name__ == "__main__":
    main()
