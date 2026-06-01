# CONFIDE — Roadmap to evidence-based / publishable

Issues distilled from an independent Codex audit (2026-06-01) of the benchmark for
scientific rigor. Ordered by the audit's impact-vs-effort ranking. Each maps to a tracked
task (R#). Status reflects the live repo.

| # | Issue | Impact | Effort | Status |
|---|---|---|---|---|
| R1 | Regenerate **all** result artifacts from current gold + add a stale-check that fails CI on drift. Stale IAA recomputes to κ 0.666→~0.850, F1 0.782→~0.896; harm-weighted recall missing from the leaderboard. | Very high | Low | open |
| R2 | Fix scoring artifacts: true non-PII char overlap (current `masked − pii_chars` can report 100% with FPs present), implement promised dev/test split reporting, rename "coverage F2" → **mask-coverage**, zero-support type filtering, type-after-merge label bug, bootstrap entity-CL weighting. | Very high | Med | open |
| R3 | Add **Presidio / Philter** baselines on identical gold + a public de-id dataset; add comparison rows to the benchmark + report; graph any unique capabilities. | Very high | Med | **in progress** |
| R4 | Replace LLM "second annotator" IAA with **2–3 human annotators + adjudication**; until then label current IAA as an LLM-assisted consistency check, not human IAA. | Very high | High | open |
| R5 | Report **N≥5 LLM inter-run variance** (mean±std, pinned model digests, seeds) for detector LLM layer and CONFIDE-Red — the repo's own policy requires N≥3 but reports are single-run. | High | Med | open |
| R6 | Make **k-anonymity defensible** or mark it illustrative: `confide_red.py` and `privacy_utility_eval.py` disagree (104.3 vs 3504 expected matches) using different priors/survivor logic. | High | Med | open |
| R7 | Add a **consented/proxy real-therapy gold subset** with newly-labeled PII — `en-real` (ai4privacy) is not therapy dialogue. Single biggest external-validity lever. | Highest | High | open |
| R8 | **Preregister metrics + small power analysis**; fix provenance contradiction (README "all synthetic" vs en-real "real"); fix `run-benchmark.sh` EN default vs BENCHMARK.md; gold nested-entity (`timur` in email) + missing `person_role` for clients c–f. | High | Low | open |

## Confirmed bugs / measurement artifacts (from the audit)

- **k-anonymity not defensible** — substring-survivor detection + coarse fixed priors; two scripts disagree. (R6)
- **Non-PII preservation math wrong** — assumes all PII masked first. (R2)
- **Coverage F2 is mask-coverage, not standard span/entity F2** — a single giant span could score P=R=1.0. Name it. (R2)
- **Type-aware after interval-merge** can assign a long wrong type over a short correct one. (R2)
- **Bootstrap entity CI** underweights duplicate sampled docs (entity grouping vs doc resampling). (R2)
- **Gold nested false entity** — `f-timur-latin` matches `timur` inside `timur.kh@example.com`. (R8)
- **`person_role` incomplete** — only clients a/b mapped; c–f null. (R8)
- **Red-team linkability too small** — one same-pair + one diff-pair = demo, not benchmark. (R5/R6)

## Validity threats / data gaps

- RU evidence = 30 synthetic docs / 1059 spans / 6 invented personas — small + templated. (R7)
- No consented real-therapy gold; `en-real` isn't therapy. (R7)
- IAA = one author-gold vs one LLM annotator on 2 sessions, no human multi-annotator adjudication. (R4)
- No established-system baseline (Presidio/Philter/Azure/AWS/GCP) on shared gold. (R3)
- No human re-identification baseline; no attacker evidence-span requirement. (R5)
- No LLM inter-run variance; CIs are doc-bootstrap only. (R5)
- No power analysis; provenance labels inconsistent. (R8)
- Languages = RU/EN only; DE/FR/ES are roadmap, not evidence.
