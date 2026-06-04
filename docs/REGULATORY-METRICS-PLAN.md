# CONFIDE-Bench — Regulatory / Identifiability Metrics — Implementation Plan (DRAFT for review)

Goal: extend the benchmark beyond detection metrics (recall/F2) with **residual-risk** metrics
that map to named regulatory concepts, and surface them in the HTML report. All four families below
were approved. This document is the implementation plan to validate before coding.

## Available data (verified)

- `results/<ds>-bench-results.json`: per combo →
  - `coverage_relaxed_per_type[TYPE] = {support,c,fp,fn,p,r,f1,f2}`
  - `entity_level = {protected,total,entity_recall,harm_weighted_recall, by_class:{direct,quasi:{recall,...}}, by_type:{TYPE:{recall,...}}}`
  - `by_split`, `members`, `n_pred`
- `results/reconstruction-results.json`:
  - `A_quasi_survival.{a,b} = {quasi_entities, survived, survival_rate, survivors_by_type:[TYPE,...]}`
  - `B_inference_attack` (per-attribute n_recovered / n_tested), `C_over_redaction.{over_redaction_rate}`
- `results/cross-session-results.json` (from `cross_session_attack.py`) — linkability source.
- Gold: `data/sessions-ru/pii-eval-ru.jsonl` (+ adversarial); each record has `doc_id`, `spans:[{start,end,text,type,identifier_class,entity_id,...}]`.
- `scoring/score_bench.py` exposes `union_preds(dataset, members, doc_ids, sha) -> {doc_id:[spans]}` (the deployed redaction mask), and `by_doc` gold loading. So per-doc recompute is feasible.
- Default scored combo per dataset is the ★ one (e.g. RU `natasha+regex+ollama ★`).

## Metric families

### 1. WP29 (Opinion 05/2014) re-identification triad
GDPR identifiability = singling out + linkability + inference. Compute per dataset for the ★ combo.

- **Singling out (k-anonymity proxy).** For each *person* (entity_id grouped by client/split), build the
  **residual quasi-identifier signature** = set of quasi-identifier (type,value) that SURVIVED redaction
  (gold quasi mention NOT covered by the deployed mask). k = number of persons in the corpus sharing an
  identical residual signature. Report: `min_k`, `frac_unique` (k==1), and mean residual-quasi count/person.
  - **Caveat (flag):** corpus N is tiny (2–6 synthetic clients) → k is bounded by N; report it as a
    *singling-out surface* proxy, not population k-anonymity. Primary number = residual-quasi-count/person.
- **Linkability.** From `cross-session-results.json`: rate at which two sessions of the same client are
  linkable via residual quasi-IDs after redaction. Report `link_rate`.
- **Inference.** From `B_inference_attack`: `attrs_recovered / attrs_tested` (already computed). Report rate.

### 2. HIPAA Safe-Harbor 18-identifier checklist
Map CONFIDE types → applicable HIPAA §164.514(b)(2) categories; a category **passes** iff its
entity-level recall == 1.0 (all mentions masked). Report per-category pass/fail + `% applicable removed`.
Proposed mapping (review): PERSON→(A names); LOCATION→(B geo <state); DATE→(C dates); PHONE→(D); EMAIL→(F);
URL→(N); ID→(G–M structured IDs: MRN/account/license/etc., collapsed); AGE→(C, ages>89 rule);
MEDICATION/PROFESSION→**not** HIPAA-18 (quasi only) → excluded from checklist, noted separately.
"Applicable" = categories with support>0 in the gold. Disclaimer: not legal certification.

### 3. GREEN / AMBER / RED gate + identifiability index (0–1)
Composite per dataset for the ★ combo.
- inputs: residual **direct-ID** count (entity_level.by_class.direct: total−protected), residual
  **special-category** count (Art. 9 → MEDICATION + any diagnosis type), k/singling-out, inference rate.
- gate: **RED** if residual direct-ID > 0; **GREEN** if direct==0 AND special-category==0 AND inference≈0
  AND frac_unique==0; **AMBER** otherwise.
- index: `1 − weighted_risk`, weights TBD (direct 0.5, special 0.2, inference 0.2, singling 0.1) → 0–1.
- Output a single "safe to send to cloud?" verdict per dataset/client.

### 4. Worst-case leak metrics
- **min coverage recall across docs**: recompute per-doc relaxed coverage recall via `union_preds` + gold;
  report `min`, `p10`, mean.
- **leaked entities per 1k tokens**: per doc, count residual gold mentions (fn under relaxed coverage) /
  (token_count/1000); report corpus mean + max. Token count = whitespace split of the doc text.

## Implementation

- New module `src/confide_eval/scoring/regulatory.py`:
  - reuse `score_bench` helpers (`union_preds`, gold loader, overlap fn) — import, don't duplicate.
  - compute families 1–4 for the ★ combo of `ru` (primary), `en`, and optional local `en-real` where applicable.
  - write `results/regulatory-results.json`.
- Report `make_tufte_report.py`: load `regulatory-results.json`; add findings subsection **f7
  "Regulatory residual-risk"** (status-strip with the gate + triad + HIPAA coverage + worst-case), a
  headline bullet, EN+RU prose. No new chart strictly required (status-strips suffice); optional small bar.
- Wiring: add to `Makefile` `report`/`rescore` targets and `run-benchmark.sh` after scoring.

## Open questions for the reviewer
1. Is the singling-out proxy (residual-quasi-count + corpus-bounded k) defensible given N≈2–6, or should
   we drop k-anonymity language entirely and call it "residual quasi surface"?
2. HIPAA type→category mapping above — any miscategorization (esp. AGE>89, ID subcategories)?
3. Gate thresholds + index weights — sensible defaults, or should the index be purely ordinal (R/A/G)?
4. Worst-case leak: is whitespace token count acceptable, or use char count / per-1k-chars?
5. Should families be computed per-client (a/b) as well as per-dataset? (re-id risk is per-person.)

---

## Review outcome — Codex-validated corrections (supersede the draft above)

The draft was reviewed against the real data shapes. Corrections (all must-fix):

### 1. WP29 triad
- **Singling out:** DO NOT call it corpus k-anonymity (N=6 clients → toy statistic). **Reuse `src/confide_eval/scoring/kanon.py`** (population-fraction estimator with `independence_caveat()`); report it as **"residual quasi surface"**; corpus-unique signatures go in an appendix only. Recompute residual quasi per person from `data/sessions-ru/pii-eval-ru.jsonl` (`client`, `spans[].{identifier_class,entity_id,type,value}`) intersected with the deployed mask from `score_bench.load_gold()` + `union_preds()`. `A_quasi_survival` (counts only) is insufficient.
- **Linkability:** use **`results/linkability-results.json.metrics.{recall,roc_auc,f1,fp,tp}`** (real pairwise metric), NOT `cross-session-results.json` (that is longitudinal *inference gain* — keep, but rename).
- **Inference:** `results/reconstruction-results.json.B_inference_attack.*.{n_recovered,n_tested}` — OK as planned.

### 2. HIPAA — rename to "HIPAA-inspired Safe-Harbor coverage" (NOT certification)
- Pass a category iff `support>0 && fn==0` (use `coverage_relaxed_per_type` for coverage, or `entity_level.by_type` for strict). 
- **AGE:** only ages >89 are HIPAA identifiers and gold has no `age_value`/`over_89` flag → mark AGE **N/A**, note it. 
- **ID:** no `id_subtype` → cannot split HIPAA G–M; report as one collapsed "structured ID" category with a note.
- **LOCATION:** note HIPAA is "smaller than state" granularity, not any location.
- **IP:** map to category O for EN-real if support appears.
- **MEDICATION/PROFESSION:** keep OUT of HIPAA-18; report separately as clinical/special-category risk (use span `confidential_status`).

### 3. Gate → "residual-risk tier" (ordinal R/A/G ONLY; no scalar weighted index)
- Drop the 0–1 index and the "safe to send to cloud?" wording (legal/operational claim, would embarrass the paper). 
- **RU only** (EN and optional local EN-real star combos have no `entity_level`).
- Inputs from stored results: residual direct = `entity_level.by_class.direct.{total-protected}`; special-category residual via span `confidential_status` (NOT an invented `DIAGNOSIS` type) and `entity_level.by_type.MEDICATION`; inference from `B_inference_attack`; linkability above base rate.
- **RED** = any residual direct ID; **AMBER** = residual special/confidential quasi OR nonzero inference OR linkability above baseline; **GREEN** = all residual-risk tests zero/near-baseline.

### 4. Worst-case leak
- Use **containment recall** (relaxed 1-char overlap is too forgiving), recompute per doc via `load_gold()` + `union_preds()` + `overlaps()/contains()`. 
- Report `min`, `p10`, mean **and the denominator**. Wording: "leaked **mentions**", not entities (optionally also deduped leaked `entity_id` count). 
- Rate = **leaked mentions per 10k characters** (not whitespace tokens — better for Russian) + raw leaked counts.

### Open-question rulings
1. Drop k-anonymity language → "residual quasi surface"; unique-signature corpus stat in appendix only.
2. Fix HIPAA mapping (AGE>89 N/A, ID collapsed, LOCATION granularity note, IP→O, med/prof = special-category not HIPAA).
3. Ordinal R/A/G only; no scalar index until pre-registered + calibrated.
4. Per-10k-characters, include raw leaked counts.
5. Compute per-client AND dataset aggregate; publish min/max/distribution, not just mean.

### Reuse, don't duplicate: `kanon.py`, `linkability-results.json`, `score_bench.{load_gold,union_preds,overlaps,contains}`.
