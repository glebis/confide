```
  ____ ___  _   _ _____ ___ ____  _____
 / ___/ _ \| \ | |  ___|_ _|  _ \| ____|
| |  | | | |  \| | |_   | || | | |  _|
| |__| |_| | |\  |  _|  | || |_| | |___
 \____\___/|_| \_|_|   |___|____/|_____|
```

# CONFIDE

**Conf**idential **F**iltering of **I**dentifying **De**tails (Locked) — the CON·F·I·DE spelling.

> *"Confide in me."* — Kylie Minogue, *Confide in Me* (1994)

> "in the name of understanding a problem should be shared"

---

CONFIDE is a **local-first, privacy-first** toolkit and benchmark for de-identifying
**psychotherapy and coaching session transcripts** — and for measuring how well that
de-identification actually holds up against re-identification. Everything runs on your
own machine; raw client data never leaves it.

The premise: to *understand* a problem with AI, the transcript has to be shared with a
model — so first it must be made safe to share. CONFIDE both does that (the anonymizer)
and tells you, honestly, when it isn't enough (the benchmark + the attacks).

## The three parts

| Part | What it is | Where |
|---|---|---|
| **CONFIDE** | The layered, local de-identification stack: deterministic regex (emails/phones/IDs/dates) → Russian NER (Natasha) → optional OpenAI Privacy Filter → local LLM (Qwen via Ollama/llama.cpp) for medications, ages, professions, contextual IDs. | `skills/session-anonymizer/` |
| **CONFIDE-Bench** | A bilingual **RU + EN** psychotherapy-transcript de-identification **benchmark** — a layered-detector ablation scored the way the field does (recall-first / entity-level / direct vs quasi-identifier), plus a privacy–utility axis. To our knowledge the first *dedicated* therapy-*dialogue* de-id benchmark — adjacent public resources cover clinical notes, legal, or generic PII, or counseling dialogue *without* PII labels (see `docs/RESEARCH-FINDINGS.md` §7). | `docs/BENCHMARK.md` |
| **CONFIDE-Red** | The **red team**: LLM-based **re-identification / de-anonymization** attacks on the redacted output — single-session inference, longitudinal cross-session linkage, quasi-identifier singling-out — aligned with the GDPR Art-29 attack taxonomy (singling-out / linkability / inference) and the Staab et al. / RAT-Bench inference-attack literature. | `src/confide_eval/redteam/*_attack.py`, `src/confide_eval/redteam/privacy_utility_eval.py` |

CONFIDE *protects*; CONFIDE-Red *attacks* — measuring what survives so "we removed the
names" is never mistaken for "this is safe to send to the cloud."

## Headline findings

- **Some quasi-PII is still LLM-dependent** — ages, professions, medications, and
  contextual/spelled-out dates are near-zero for regex + NER; the local LLM improves
  coverage but still leaves measurable gaps.
- **Removing direct identifiers is necessary but not sufficient** — quasi-identifiers
  survive and an LLM attacker can still infer attributes, especially across multiple
  sessions of the same person.
- **Bigger isn't automatically better** — deterministic rules handle numeric dates and
  structured IDs faster and more reproducibly than a heavy transformer; OPF is kept as a
  comparison layer, not the Russian default.
- **Harm ≠ identifier-strength** — an email is a strong linker but low therapy-harm, while
  a *medication* implies a diagnosis. CONFIDE therefore reports **harm-weighted recall**
  alongside plain recall; the gap between the two is itself a finding (see
  [`HARM-TAXONOMY.md`](HARM-TAXONOMY.md)).

## Storage & isolation (real data)

CONFIDE is local-first. For real session data: **`THREE-LOCKS.md`** (device + encrypted
store + per-file/isolation, with a storage checklist) and **`ISOLATION.md`** (red/green
flow, no-network containers, macOS VMs, sops/age encryption). Extend the benchmark with
public datasets via `python3 confide.py datasets list` (see `docs/DATASETS.md`).

## Reproducibility & ethics

Pinned environment + Docker (`Dockerfile`, `requirements.lock`), an append-only
run registry (`caches/runs/`), and full docs: `docs/REPRODUCIBILITY.md`, `docs/ETHICS.md`,
`docs/DATASHEET.md`, `docs/EXPLAINER.md`.

A benchmark is only as trustworthy as its reporting choices are explicit.
[`docs/REPORTING.md`](docs/REPORTING.md) documents exactly what CONFIDE puts in the headline
and what it leaves out, and why — recall-led (a missed leak is the real failure), no raw
real data, the OPF privacy filter kept as a lesson rather than a recommendation, and no
re-identification recipe.

## Documentation map

| Doc | What it answers |
|---|---|
| **Method & results** | |
| [`docs/REPORTING.md`](docs/REPORTING.md) | What the benchmark includes/omits, and why (recall-led, no raw data, no re-id recipe). |
| [`docs/RESEARCH-FINDINGS.md`](docs/RESEARCH-FINDINGS.md) | Deep-research positioning vs prior de-id benchmarks, methods, and datasets (needs-verification). |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) | The full layered-detector ablation results and scoring method. |
| [`results/CONFIDE-RED-RESULTS.md`](results/CONFIDE-RED-RESULTS.md) | Red-team re-identification results (inference / singling-out / linkability). |
| **Data** | |
| [`docs/DATASHEET.md`](docs/DATASHEET.md) | Datasheet / data statement: provenance, composition, limits of the synthetic corpus. |
| [`docs/DATASETS.md`](docs/DATASETS.md) | Public datasets to extend the benchmark, fetched via the CLI. |
| **Severity & privacy** | |
| [`HARM-TAXONOMY.md`](HARM-TAXONOMY.md) | Why harm ≠ identifier-strength, and how harm-weighted recall is computed. |
| [`docs/ETHICS.md`](docs/ETHICS.md) | Ethics statement and responsible-use policy (ACL / NeurIPS / Menlo / Belmont norms). |
| [`ISOLATION.md`](ISOLATION.md) | Red/green data flow, no-network containers, macOS VMs, sops/age encryption. |
| [`THREE-LOCKS.md`](THREE-LOCKS.md) | Device + encrypted store + per-file isolation, with a storage checklist for real data. |
| **Reproducibility** | |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | Keeping the benchmark comparable over time; versioning, re-run policy, cost. |
| [`docs/SOURCES.md`](docs/SOURCES.md) | Primary/near-primary sources checked for publishable methodology claims. |
| [`requirements.lock`](requirements.lock) | Pinned dependencies for a deterministic environment. |
| [`Dockerfile`](Dockerfile) / [`run-benchmark.sh`](run-benchmark.sh) | Containerised, one-command benchmark run. |
| **Plain-language** | |
| [`docs/EXPLAINER.md`](docs/EXPLAINER.md) | ELI5 → ELI14 explainer plus ready-to-paste blurbs for non-specialists. |

> ⚠️ **Provenance, stated precisely.** Every **therapy/coaching transcript** in this
> repository (the RU and EN-synth sessions) is **fully synthetic** — fictional clients,
> invented identifiers; no real client data ever enters it and none must. The one
> exception is **EN-real**, a small slice of the public `ai4privacy/pii-masking-300k`
> benchmark: that is **generic, non-therapy, non-clinical** PII text used only as an
> **external anchor** for the EN detectors. It contains **no real therapy/clinical data**,
> but it is *not* "synthetic" the way the therapy corpus is — it is real generic PII from a
> public dataset, carried unmodified under that dataset's license. CONFIDE-Red attacks run
> only against the fabricated therapy personas. Benchmark performance is **not** HIPAA or
> GDPR anonymisation certification.

CONFIDE grew out of the *Psychodemia · AI & Mental Health* masterclass (31 May 2026); the
original masterclass materials are in `README-masterclass.md`.
