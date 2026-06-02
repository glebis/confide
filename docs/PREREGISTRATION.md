# Preregistration — CONFIDE-Bench

A **methods preregistration** for the CONFIDE-Bench de-identification benchmark: it fixes
the metrics, detector combinations, and dev/test protocol **before** any publishable
comparison, and states honestly how much the corpus can and cannot support.

> **Scope.** This is a preregistration for a **small, mostly synthetic** therapy-transcript
> de-identification benchmark — *not* a clinical trial. There is no human-subjects
> intervention, no treatment arm, and no clinical endpoint. "Power" here means
> *measurement precision on detector recall*, quantified by document-level bootstrap CIs,
> not statistical power to detect a clinical effect. Pairs with `BENCHMARK.md` (results),
> `REPORTING.md` (what is included/omitted and why), `DATASHEET.md` (data provenance), and
> `REPRODUCIBILITY.md` (re-run policy).

---

## 1. Fixed metrics (declared before comparison)

**Headline metrics** (the numbers a system is judged on):

1. **Entity-level recall (TAB-style).** An entity (grouped by `entity_id`) is *protected*
   only if **all** its mentions are masked; one surviving mention re-identifies. This is
   the rigorous primary metric.
2. **Mask-coverage F2 (β=2).** Recall-weighted coverage F-score; a missed identifier (false
   negative) is a leak and costs more than an over-mask (false positive), so β=2.
3. **Harm-weighted recall.** Entity recall weighted by the per-type harm level
   (`HARM-TAXONOMY.md`) — an email and a medication are not equally damaging. Reported
   **alongside** plain recall; the gap between the two is itself a result.

**Secondary metrics** (context and failure-mode diagnosis, *not* used to rank systems):

- **Mask-coverage recall** (does any prediction touch the gold span).
- **Per-type recall** (which layer catches AGE / DATE / MEDICATION / PERSON / …).
- **Direct vs quasi-identifier split** (quasi-identifiers survive more and re-identify in
  combination).
- **Strict (exact-span) and containment (≥80%) recall** as boundary-sensitivity checks.

Precision and micro/macro-F1 are reported as guardrails (so over-redaction is visible) but
are **never** the headline. No accuracy. Rationale: full detail in `REPORTING.md` §1–§3.

## 2. Fixed detector combinations and the ★ default

The ablation combinations are **fixed** in `score_bench.py` (`COMBOS`) and are not changed
post hoc to favour a result. The proposed default stack (★) per language:

| Dataset | Fixed ★ default stack |
|---|---|
| **RU-synth** | `natasha + regex + ollama` ★ |
| **RU-adversarial** | `natasha + regex + ollama` ★ |
| **EN-synth** | `opf + regex + ollama` ★ |
| **EN-real** | `opf + regex + ollama` ★ |

The ★ default is what `run-benchmark.sh` and `score_bench.py` report as the headline stack;
Presidio and Philter are carried as **external baselines** (separate rows), not as part of
the ★ stack. The full set of ablation combos (single layers and their unions) is enumerated
in `score_bench.py` and is identical across runs.

## 3. Dev / test protocol (no tuning on test)

The corpus is **person-disjoint** by construction — each synthetic client is a distinct
person, so splitting by client prevents profile/template leakage:

- **dev** = RU clients **a / c / e** (15 docs, 526 spans) — any threshold/prompt inspection
  happens here.
- **test** = RU clients **b / d / f** (15 docs, 532 spans) — held out; reported for
  generalization only.

**Nothing is tuned on test.** The per-split headline sub-table in `BENCHMARK.md` is
**reporting only**; it exists so the dev→test generalization gap is visible *before* any
cross-population claim. (Observed RU gap: test entity recall 0.63 vs dev 0.70 — the expected
person-disjoint generalization drop on a small corpus.)

## 4. Uncertainty quantification (preregistered = the document-level bootstrap CIs)

Uncertainty is the **nonparametric document-level bootstrap** (`bootstrap_ci.py`, 2000
resamples, fixed seed 20260601, doc-level resampling with correct entity reweighting). The
**current CI widths** (committed in `*-bootstrap-ci.json`):

| Dataset (★) | N docs | Coverage recall (95% CI) | Entity recall (95% CI) |
|---|--:|---|---|
| **RU-synth** | 30 | 0.837 (0.808–0.864), half-width ≈ ±0.028 | 0.625 (0.572–0.673), half-width ≈ **±0.050** |
| **RU-adversarial** | 16 | 0.95 (0.842–1.00), half-width ≈ ±0.079 | 0.95 (0.842–1.00) |
| **EN-synth** | 32 | 0.892 (0.800–0.976), half-width ≈ ±0.088 | (mention-level; no entity grouping) |
| **EN-real** | 15 | 0.894 (0.789–0.964), half-width ≈ ±0.088 | (mention-level) |

These intervals — not significance stars — are the preregistered uncertainty report. Point
estimates are treated as **directional**; every headline is quoted with its CI.

## 5. Power / precision analysis (small and honest)

For the primary corpus (RU-synth, **N = 30 docs / 1,058 gold spans**), the observed
document-level bootstrap **half-width on entity recall is ≈ ±0.05** (95% CI 0.572–0.673).
Treating that half-width as the precision of a single-system estimate, the **minimum
detectable difference (MDD)** between two systems evaluated on the *same* 30 documents — for
a non-overlap of independent 95% CIs — is on the order of **≈ 0.10 absolute** on entity
recall (roughly the sum of two ~±0.05 half-widths; less when the comparison is paired on the
same docs, but still ~0.07–0.10 in practice at this N). Coverage recall is tighter (≈ ±0.028
half-width → MDD ≈ 0.05–0.06).

**Consequence — the corpus is underpowered for small effects.** Differences below ≈ 0.10
entity recall (≈ 0.05 coverage recall) on RU, and larger on the smaller EN / EN-real / adv
sets (half-widths ≈ ±0.08), **cannot be distinguished from noise** at this N. Therefore:

- System comparisons are reported **with confidence intervals, not significance stars**, and
  we **do not** claim a winner when CIs overlap.
- Only differences that exceed the relevant MDD (and survive on the held-out test split) are
  reported as real; everything smaller is explicitly called **directional**.
- Growing N (more synthetic clients; a future consented/proxy real subset, `ROADMAP.md` R7)
  is the stated path to tightening these intervals.

This analysis is deliberately modest: it bounds what *this* benchmark can claim, and is not
a substitute for evaluation on consented real data before any deployment decision.

---

*Registered as the fixed analysis plan for CONFIDE-Bench. Changes to metrics, the ★ default,
or the dev/test split after this point are amendments and will be logged as such.*
