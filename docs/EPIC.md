# EPIC — CONFIDE: from prototype to publishable de-identification benchmark

**Epic goal.** Turn CONFIDE from a strong prototype into a benchmark whose every headline
number a peer reviewer can trust — credible gold (human-adjudicated), an external-system
baseline, reported uncertainty *and* LLM run-variance, defensible re-identification claims,
and at least a foothold of real (not synthetic) therapy evidence.

**Epic-level definition of done.**
- Gold has **human inter-annotator agreement + adjudication** (not LLM-only).
- Every metric is **named for what it measures**, reported with **CIs**, and reproducible from a green **stale-check**. ✅ (R1/R2)
- An **established baseline** (Presidio/Philter) is scored on shared + public data. ✅ (R3)
- Re-identification (CONFIDE-Red / k-anonymity) is either **defensible or labelled illustrative**.
- LLM layers report **N≥5 variance**; a **larger local model** is evaluated on long docs.
- At least one **consented/proxy real-therapy** slice with fresh PII labels.
- All external citations **verified** (no fabricated/mis-stated references).

---

## Status snapshot

| Done ✅ | In flight 🔄 | Remaining ⬜ |
|---|---|---|
| R1 artifacts+stale-check · R2 scoring fixes · R3 Presidio/Philter · R8 prereg+provenance+gold bug | R4 (this epic frames it) · citation audit (running) | R7 real gold · R5 variance · R6 k-anon · R9 bigger model · R1-CI hookup · stretch items |

---

## Prioritized backlog (by impact, then effort)

Impact = how much it moves "publishable / trustworthy". Effort = wall-clock incl. humans.
Owner: **🤖 agent** (I can do solo) · **🧑 human** (needs you/people) · **⏱ compute** (needs a run, ideally the Mini).

| Rank | Task | Impact | Effort | Owner | Status |
|---:|---|---|---|---|---|
| **P0** | **T1 / R7** — Consented or proxy **real-therapy gold** slice | 🔴 Highest | High | 🧑+🤖 | ⬜ |
| **P0** | **T2 / R4** — **Human multi-annotator IAA + adjudication** | 🔴 Very high | High | 🧑+🤖 | ⬜ |
| **P1** | **T3 / R6** — Make **k-anonymity / CONFIDE-Red** defensible or label illustrative | 🟠 High | Med | 🤖 | ⬜ |
| **P1** | **T4 / R5** — **N≥5 LLM run-variance** (detector + CONFIDE-Red), mean±std | 🟠 High | Med | ⏱🤖 | ⬜ |
| **P2** | **T5 / R9** — **Larger local model** on long RU docs (recover the collapsed LLM layer) | 🟡 Med-high | Med | ⏱ | ⬜ |
| **P2** | **T6** — **Relative-date recognizer** (the one additive capability Presidio had) | 🟡 Med | Low | 🤖 | ⬜ |
| **P3** | **T7 / R1-CI** — Wire `check_artifacts.py` into **CI** (`.github/`) | 🟢 Med-low | Low | 🤖 | ⬜ |
| **P3** | **T8** — Expand **CONFIDE-Red linkability** beyond 1 pair (real benchmark, not demo) | 🟢 Med-low | Med | ⏱🤖 | ⬜ |
| **P4** | **T9** — **DE/FR/ES** language extension (roadmap → evidence) | ⚪ Future | High | 🧑+🤖 | ⬜ |

---

## Detailed task specs

### T1 / R7 — Real-therapy gold slice  ·  P0 · Highest impact · High effort · 🧑+🤖
**Problem.** All therapy evidence is synthetic (30 docs, 6 invented personas); `en-real`
(ai4privacy) is generic, non-therapy PII. External validity is the single biggest gap — a
de-id method tuned on templated synthetic dialogue may not transfer to real speech.
**Why it's highest impact.** One credible real slice changes the claim from "works on our
fakes" to "works on real therapy language." Nothing else moves validity as much.
**Work breakdown.**
- [ ] Decide the source: (a) your own/consented sessions (consent + ethics per `ETHICS.md`; therapist-side data needs care), or (b) a public counselling-dialogue proxy (e.g. transcribed counselling corpora) with fresh PII labelling.
- [ ] Obtain/record explicit consent + scope; log it. RED stays local (`THREE-LOCKS.md`).
- [ ] Label PII spans on the slice using the **codebook from T2** (same taxonomy/harm).
- [ ] Run the stack **stats-only, locally** (`real_session_eval.py`) — only aggregates leave the machine; never raw text.
- [ ] Report distributions + per-type recall vs the synthetic corpus; name the transfer gap.
**Acceptance / DoD.** ≥1 real (or consented-proxy) slice with labelled PII; aggregate recall reported with CIs; zero raw PII committed; consent recorded.
**Dependencies.** T2 codebook (shared labelling rules). **Owner split.** 🧑 consent + being/recruiting labeller; 🤖 harness, stats-only eval, reporting.
**Risks.** Consent/ethics is the gate; wall-clock days–weeks. Mitigate by starting the public-proxy path in parallel so progress isn't blocked on consent.

### T2 / R4 — Human multi-annotator IAA + adjudication  ·  P0 · Very high · High · 🧑+🤖
**Problem.** Gold authored by one person; "IAA" was one **LLM** on **two** sessions vs the author's own planted labels — circular, not human agreement. Relabelled honestly as an *LLM-assisted consistency check* (R1/R8); R4 makes it real.
**Why.** The gold is the ruler. Without human IAA the whole leaderboard measures "agreement with one author." κ is the credibility certificate reviewers demand.
**Work breakdown.**
- [ ] **🤖 Draft the annotation codebook** — PII taxonomy, span-boundary rules, rulings on quasi-identifiers, partial/spelled-out values, dates, third-party names, harm levels. (The real intellectual work; I can do this now.)
- [ ] **🤖 Build the annotation harness** — serve spans, collect blind labels, compute pairwise **Cohen's κ** / **Fleiss' κ** (3+), span/entity-level F1, and a disagreement report; track adjudication decisions.
- [ ] **🤖 Stratified sample** — ~6–10 sessions covering every PII type + the known edge cases.
- [ ] **🧑 2–3 independent humans** label the sample **blind** to each other and the author-gold.
- [ ] Compute + report **pre-adjudication** κ.
- [ ] **🧑 Adjudicate** disagreements → final adjudicated gold; document rules; report **post-adjudication** κ.
**Acceptance / DoD.** ≥2 human annotators on the stratified sample; pre- and post-adjudication κ reported; codebook committed; `IAA-RESULTS.md` reflects human IAA (LLM pass demoted to a labelled stopgap).
**Dependencies.** None to start the 🤖 parts. **Owner split.** 🤖 codebook+harness+sample (turnkey now); 🧑 the labelling + adjudication.
**Risks.** Recruiting annotators (days–weeks). Mitigate: I produce everything so a human only spends a few focused hours; optionally add a *second independent LLM* (different model, blind prompt) as a clearly-labelled interim third annotator — never a human substitute.

### T3 / R6 — Defensible k-anonymity / CONFIDE-Red  ·  P1 · High · Med · 🤖
**Problem.** `confide_red.py` and `privacy_utility_eval.py` give **different** expected-match
counts for the same client (104.3 vs 3504) — different priors + substring survivor detection;
"toy demo, not evidence" (audit B1). `privacy_utility` also ignores some survivor types in `dims_used`.
**Why.** A re-identification claim with two contradictory numbers is worse than none.
**Work breakdown.**
- [ ] Unify on **one** survivor-detection method (entity-aware, not raw substring) shared by both scripts.
- [ ] Replace coarse fixed fractions with **documented value-level population priors** (cite sources) + an **independence caveat**.
- [ ] Add a **sensitivity analysis** (vary priors ±, show the singling-out verdict's robustness).
- [ ] If priors can't be defended, **label singling-out "illustrative"** everywhere and stop quoting point counts.
- [ ] Reconcile the two scripts so they agree (or document why they legitimately differ).
**Acceptance / DoD.** One method, one number per client (or an explicit illustrative label); priors sourced; sensitivity reported; `BENCHMARK.md`/results consistent; stale-check green.
**Dependencies.** None. **Owner.** 🤖. **Risks.** Defensible priors for RU personas may not exist → fall back to "illustrative" (still a valid, honest outcome).

### T4 / R5 — N≥5 LLM run-variance  ·  P1 · High · Med · ⏱🤖
**Problem.** `REPRODUCIBILITY.md` requires N≥3 runs; all numbers are single-run. LLM layers
are non-deterministic — and we already saw qwen2.5:3b **collapse** on long RU docs.
**Why.** A single LLM run isn't reproducible evidence; reviewers want mean±std + seeds.
**Work breakdown.**
- [ ] Pin model **digests** (record `ollama show` hash) + seeds/configs.
- [ ] Run the **LLM detector layer ×5** per dataset; report **mean±std** of entity recall / harm-weighted recall.
- [ ] Run **CONFIDE-Red ×5** (inference/linkability) → mean±std of recovery.
- [ ] Add variance columns/notes to `BENCHMARK.md`; update `REPRODUCIBILITY.md`.
**Acceptance / DoD.** N≥5 reported with mean±std, pinned digests + seeds; stale-check green.
**Dependencies.** Best run **after T5** (use the better model) or alongside. **Owner.** ⏱ compute (ideal on the Mini overnight), 🤖 orchestration. **Risks.** Compute-heavy (~hours, contention-sensitive) — schedule uncontended.

### T5 / R9 — Larger local model on long docs  ·  P2 · Med-high · Med · ⏱
**Problem.** qwen2.5:3b: entR **0.157** on 32K-char RU docs (2 docs JSON-errored) → `natasha+regex` alone ≈ full stack. The LLM layer adds nothing *at 3B on long docs*.
**Why.** Recovers the LLM-only types (medication/age/date/profession) the deterministic layers can't — the reason an LLM layer exists.
**Work breakdown.**
- [ ] Re-run RU LLM detector + CONFIDE-Red with **qwen2.5:14b** (q4 ~9 GB; fits 24 GB only uncontended) and, if RAM allows, 32b — best on a **48–64 GB Mini**.
- [ ] Compare entity recall + ms/doc vs 3b; check JSON-error rate drops.
- [ ] If 14B materially helps, make it the RU default and note the hardware floor.
**Acceptance / DoD.** Head-to-head 3b vs 14b(/32b) table (recall + ms/doc + error rate); recommendation recorded. **Dependencies.** Hardware (Mini) for comfortable runs. **Owner.** ⏱. **Risks.** 24 GB swaps on 14B+ under load → the Mini is the clean fix.

### T6 — Relative-date recognizer  ·  P2 · Med · Low · 🤖
**Problem.** Presidio's `DATE_TIME` caught **relative/colloquial dates** ("last Tuesday", "19th of the month") the stack misses — the one genuinely additive capability found in R3.
**Why.** Low effort, closes a real recall gap on a quasi-identifier type.
**Work breakdown.**
- [ ] Add a relative-date recognizer (regex + small list) to the regex layer (RU + EN).
- [ ] Re-score; confirm DATE recall rises without precision collapse; update tables.
**Acceptance / DoD.** DATE recall improves on EN-synth; no precision regression; stale-check green. **Owner.** 🤖. **Risks.** Over-matching common words → keep patterns tight, test FPs.

### T7 / R1-CI — Wire stale-check into CI  ·  P3 · Med-low · Low · 🤖
**Problem.** `check_artifacts.py` exists + passes but isn't enforced; there's a `.github/`.
**Work breakdown.** [ ] Add a GitHub Action (or pre-commit) running `make check` (+ deterministic re-score) on push; fail on drift. [ ] Document in `REPRODUCIBILITY.md`.
**DoD.** CI fails on a deliberately drifted artifact. **Owner.** 🤖.

### T8 — Expand CONFIDE-Red linkability  ·  P3 · Med-low · Med · ⏱🤖
**Problem.** Linkability tests **one** same-client + **one** diff-client pair — a demo, not a benchmark (audit B8).
**Work breakdown.** [ ] All same/different session pairs across clients; report ROC/accuracy with CIs. [ ] Tie to T4 variance.
**DoD.** Linkability over the full pair matrix with CIs. **Owner.** ⏱🤖.

### T9 — DE/FR/ES extension  ·  P4 · Future · High · 🧑+🤖
**Problem.** Novelty claim spans 5 languages; only RU/EN have evidence.
**Work breakdown.** [ ] Synthetic DE/FR/ES corpora (per-language NER: spaCy/Stanza). [ ] Gold + codebook per language. [ ] Score + baseline.
**DoD.** ≥1 non-RU/EN language with gold + scores. **Owner.** 🧑+🤖. **Note.** Gate behind the citation audit's verdict on the cross-language novelty claim.

---

## Recommended sequencing

1. **Now, in parallel (no humans needed):** T2 codebook + harness, T3 k-anon, T6 relative-date, T7 CI — all 🤖, all unblock or de-risk later work. The **T2 codebook also unblocks T1 + T9**.
2. **Schedule on the Mini (overnight, uncontended):** T5 bigger model → then T4 variance → T8 linkability — the compute chain.
3. **Start the human track early (longest wall-clock):** recruit T2 annotators + T1 consent in parallel with the 🤖 work, since they gate the two highest-impact tasks.

**Critical path to "publishable":** T2 (human IAA) and T1 (real gold) — both human/consent-bound, weeks of wall-clock. Everything else is hours and can land first. Start the human track today; do the 🤖/compute backlog while it runs.
