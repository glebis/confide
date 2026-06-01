# CONFIDE — What the report includes, what it omits, and why

A benchmark is only trustworthy if its reporting choices are explicit. This documents
**what CONFIDE puts in the headline, what it deliberately leaves out, and the reasoning** —
so a reader can judge the numbers rather than take them on faith. (Pairs with
`DATASHEET.md` for the *data*, `HARM-TAXONOMY.md` for severity, `ETHICS.md` for scope.)

## 1. The headline metric — and why it's recall-weighted

- **Headline: entity-level recall and F2 (β=2), not F1 or accuracy.** In de-identification
  a **false negative is a leaked person**; a false positive is a redacted word. The costs
  are asymmetric, so we weight recall over precision (F2) and lead with recall. Reporting
  F1/accuracy as the headline would hide leaks behind precision.
- **We still report precision** (per-type, decoupled) so over-redaction is visible — an
  anonymizer that masks everything gets recall 1.0 but destroys utility. Precision is the
  guardrail, not the goal.

## 2. What the report INCLUDES (and why each earns its place)

| Included | Why |
|---|---|
| **Entity-level recall (TAB-style)** | An entity is protected only if **all** its mentions are masked — one surviving mention re-identifies. Mention-level recall over-credits partial coverage. |
| **Harm-weighted recall** | Plain recall treats an email like a medication. Therapy harm ≠ token count (`HARM-TAXONOMY.md`). Reported **alongside**, not instead — the gap is the finding. |
| **Direct vs quasi-identifier split** | Quasi-identifiers (age, city, profession) survive more and re-identify in combination; a single number hides this. |
| **Per-layer ablation** (regex / Natasha / LLM and unions) | Shows *which layer catches what* — the practical "what stack for what language" answer, and reproducible attribution. |
| **Per-type recall table** | Surfaces the specific failure modes (e.g. MEDICATION/AGE only recovered by the LLM). |
| **CONFIDE-Red: inference / singling-out / linkability** | Coverage ≠ safety. Maps to the three GDPR Art-29 / Anonymeter attacks — measures residual *re-identification* after redaction. |
| **IAA (Cohen's κ, independent annotator)** | A gold standard one person wrote is an opinion; agreement makes it a measurement. |
| **Run records (lm-eval-harness style JSON/JSONL)** | Every headline number is traceable to a logged run with code/docs hashes. |

## 3. What the report OMITS — and why

- **No real personal-session transcripts, ever.** Real sessions are processed **stats-only,
  locally** (`real_session_eval.py`, `privacy=real-local-statsonly`); only **aggregates**
  leave the machine. We omit raw real text by design — that's the entire thesis, and the
  numbers on real data are reported as distributions, never examples (`ETHICS.md`).
- **OPF is not a default layer** — it's reported as a **lesson, not a recommendation.** On
  CPU it ran ~2 s/line, didn't finish 10 KB docs, and broke JSON; its one RU advantage
  (dates) was recovered by a date regex at ~500× the speed. We keep the measurement to show
  *why* it was replaced, and omit it from the recommended stack.
- **Precision is not the headline** (see §1) — included but never leading.
- **No accuracy / no micro-F1-as-headline.** Class imbalance (PERSON dominates) makes a
  single micro number flattering; we report **per-type** and **macro** so rare-but-critical
  types (MEDICATION) aren't drowned out.
- **CONFIDE-Red successes are reported as rates on synthetic personas, not as recovered
  identities.** We omit any worked example of *how* to re-identify a real person — the suite
  measures resistance; it is not a de-anonymization recipe. Attributes are fabricated.
- **Single-model attacker numbers are labelled, not generalized.** CONFIDE-Red ran with one
  small local model (qwen2.5:3b); we report that attacker's results and explicitly do **not**
  claim them as an upper bound — a frontier attacker would do better. Stated as a floor.
- **Small-N caveats are kept visible, not smoothed.** The corpus is synthetic and modest
  (30 docs / 713 spans); we report bootstrap CIs and avoid significance claims the N can't
  support. We omit point-estimate comparisons that the CI would swallow.
- **"Sensitive disclosure" content is named as a gap, not scored.** The most damaging
  therapy leaks (trauma, orientation) aren't a PII type and aren't in the gold; we flag the
  gap (`HARM-TAXONOMY.md`) rather than report a number we can't yet defend.

## 4. Aggregation choices

- **Macro over types** for the cross-type headline (every type counts equally, so rare
  high-harm types matter); **micro/per-type** also shown for completeness.
- **dev/test split** (clients a/c/e vs b/d/f) reported separately; we omit any tuning on
  test.
- **Unions are interval-merged** before scoring (overlapping spans from different layers
  don't double-count) — a methodological fix, noted so results are comparable across layers.

## 5. Non-claims (what these numbers do NOT mean)

- Not a compliance certificate (152-ФЗ / GDPR) — a measurement, not legal assurance.
- Not a guarantee that GREEN output is safe to publish — residual risk is *measured*
  (CONFIDE-Red), not eliminated; human review remains required.
- Not a clinical tool — the harm levels are starting points for clinician review, not fixed
  weights.
- Synthetic-corpus numbers are an estimate of method behaviour, not of any real client's risk.

**One sentence:** CONFIDE leads with recall and harm-weighted recall because leaks are the
cost that matters, reports precision/ablations/attacks as guardrails and context, and omits
raw real data, precision-as-headline, OPF-as-default, and any re-identification recipe — each
omission for a stated reason, not for convenience.
