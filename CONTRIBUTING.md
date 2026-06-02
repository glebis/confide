# Contributing to PsychoPII

Thanks for your interest. PsychoPII is a **community / citizen-science** benchmark for
de-identifying psychotherapy transcripts. It is built and maintained by **volunteers**,
not a funded research lab — contributions, scrutiny, and corrections are exactly what
make it trustworthy. Please read this before opening an issue or PR.

## What this project is (and is not)

- It **is** an open, reproducible measurement harness + synthetic dataset for comparing
  de-identification tools, with a privacy/utility/re-identification lens.
- It is **not** peer-reviewed, clinically validated, or a compliance product. See
  `DISCLAIMER.md` and `docs/ETHICS.md`.

## Ground rules (privacy first)

1. **Never commit real personal data.** No real transcripts, names, phones, emails,
   IDs, or any PII — in code, tests, issues, or PRs. Synthetic/fictional only.
2. **Do not paste real session text into issues.** If you hit a bug on real data,
   reproduce it on synthetic data or report only aggregate statistics (no text).
3. **Anonymize before you share.** If you must show output, use the local pipeline and
   review it by hand first; remember the benchmark's own finding that ~quarter–third of
   quasi-identifiers survive automatic redaction.
4. Real-data evaluation must follow `docs/ETHICS.md` §5 (consent incl. third parties,
   local-only processing, no re-identification).

## How to contribute

### Issues
- **Bug reports:** include the command, the *synthetic* input (or a minimal repro),
  expected vs actual, and your environment (OS, Python, model versions). Use the
  detector **manifests** (`caches/detector-cache/*.manifest.json`) to report code/data shas.
- **Data-quality / gold corrections:** point to the span and the reason. Gold is a
  *planted-signal* standard validated by IAA — disagreements are welcome and tracked as
  adjudication candidates (see `results/IAA-RESULTS.md`).
- **New language / dataset proposals:** see `docs/RESEARCH-MULTILINGUAL.md` for the
  extension recipe; propose taxonomy mapping + a shareable, consented data source.
- Label issues: `bug`, `gold`, `metric`, `privacy`, `language:<xx>`, `docs`,
  `good-first-issue`.

### Pull requests
- Keep changes focused; match the surrounding style (terse, documented, no new heavy deps
  without discussion).
- **Tests required for scoring/detector changes.** Re-run the affected
  `score_bench.py` / detector and include the before/after numbers. For privacy-sensitive
  scripts, include or update a **leak-safety self-test** (see `src/confide_eval/scoring/real_session_eval.py`).
- **Reproducibility:** if you change a detector, re-run `run_detectors.py` so manifests
  update; if you change gold, re-run the scorer + `make_benchmark.py`.
- Do not mix vendor/model-card claims into measured results.
- Sign-off: by submitting, you confirm your contribution contains **no real PII** and is
  yours to license under the repo license.

## Review & acceptance

- Maintainers review for: privacy safety, correctness, reproducibility, and honest
  reporting (recall-first; limitations stated; preprint citations flagged).
- Adversarial review is encouraged — if you can show a metric is gameable, a gold span is
  wrong, or a script can leak, that's a high-value contribution.
- Expect requests for a synthetic repro before any real-data-adjacent change is merged.

## Scope of accepted contributions

✅ welcome: bug fixes, metric rigor, new adversarial cases, language extensions, dataset
mappings, documentation, citation verification, leak-safety hardening.

⛔ out of scope: anything requiring real patient data in the repo; "compliance
certification" claims; attack tooling aimed at real individuals; detection-evasion for
deployment against people.

By participating you agree to keep the project honest about its limits — see
`DISCLAIMER.md`.
