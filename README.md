```
  ____ ___  _   _ _____ ___ ____  _____
 / ___/ _ \| \ | |  ___|_ _|  _ \| ____|
| |  | | | |  \| | |_   | || | | |  _|
| |__| |_| | |\  |  _|  | || |_| | |___
 \____\___/|_| \_|_|   |___|____/|_____|
```

# CONFIDE

**Conf**idential **F**iltering of **I**dentifying **De**tails (Locked) — the CON·F·I·DE spelling.

> But in the name of understanding
> Our problems should be shared
>
> — Kylie Minogue, [*Confide In Me*](https://www.youtube.com/watch?v=PxZkjq9z5wg) — the song this project's name plays on.

---

CONFIDE is a **local-first, privacy-first** toolkit and benchmark for de-identifying
**psychotherapy and coaching session transcripts** — and for measuring how well that
de-identification actually holds up against re-identification. Everything runs on your
own machine; raw client data never leaves it.

The premise: to *understand* a problem with AI, the transcript has to be shared with a
model — so first it must be made safe to share. CONFIDE both does that (the anonymizer)
and tells you, honestly, when it isn't enough (the benchmark + the attacks).

## Why this exists

Therapists and coaches increasingly want AI to help them review sessions, spot patterns,
and prepare — but a session transcript is among the **most sensitive data a person ever
produces**. It can name a diagnosis, a medication, an employer, an abuser, a sexual
orientation, a suicidal moment. Pasting it into a cloud model can leak all of that, and
the harm is not hypothetical: stigma, discrimination, loss of work, danger to someone
fleeing abuse. Russia's 152-ФЗ and the EU's GDPR both treat this as special-category data
with heavy penalties — but **compliance is the floor, not the point**; the point is not
hurting the people who trusted a therapist with their story.

The honest problem is that "we removed the names" is routinely mistaken for "this is safe
to send." It usually isn't: quasi-identifiers (age + profession + a small city) and a
stigmatised disclosure can re-identify someone after every name is gone. Yet there was **no
public benchmark** that measured de-identification on *therapy dialogue* specifically — the
existing de-id datasets are clinical notes, court records, or generic PII, not the messy,
disclosive back-and-forth of a real session.

CONFIDE exists to (1) make a transcript **safe to share locally, before anything reaches a
cloud**, and (2) **measure, out loud, how safe it actually is** — including by attacking its
own output. It is deliberately built in the open, by volunteers, so the people whose
privacy is at stake can inspect exactly how it works.

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
  [`docs/HARM-TAXONOMY.md`](https://github.com/glebis/confide/blob/main/docs/HARM-TAXONOMY.md)).

## Storage & isolation (real data)

CONFIDE is local-first. For real session data: **`docs/THREE-LOCKS.md`** (device + encrypted
store + per-file/isolation, with a storage checklist) and **`docs/ISOLATION.md`** (red/green
flow, no-network containers, macOS VMs, sops/age encryption). Extend the benchmark with
public datasets via `python3 confide.py datasets list` (see `docs/DATASETS.md`).

## Ethics & responsible use

CONFIDE is a privacy tool about vulnerable people; the ethics are not an afterthought.
Full statement in [`docs/ETHICS.md`](https://github.com/glebis/confide/blob/main/docs/ETHICS.md); the load-bearing commitments:

- **AI here is a microscope, not a surgeon.** It is for de-identification and analysis
  support — **never** for suicide/crisis-risk assessment, diagnosis, or automated decisions
  about a person's care. Risk assessment is always a human's job. A clinician stays in the
  loop; the tool informs, it does not decide.
- **No real data in public, ever.** Every therapy transcript shipped here is **synthetic**
  (fictional clients) — so this is **not human-subjects research** and exposes no one. Real
  or consented sessions are processed **only locally**, stats-only, behind device + store +
  file encryption ([`docs/THREE-LOCKS.md`](https://github.com/glebis/confide/blob/main/docs/THREE-LOCKS.md), [`docs/ISOLATION.md`](https://github.com/glebis/confide/blob/main/docs/ISOLATION.md)); only
  aggregates ever leave the machine, never transcript text.
- **Consent and scope.** Use real data only with explicit consent and only your own /
  consented sessions; therapist-side recordings need particular care.
- **Dual-use, handled openly.** The red team (CONFIDE-Red) re-identifies redacted text — the
  same measurement could be misused. We counter this by **headlining recall** (a miss is a
  leak), reporting residual risk as rates on fabricated personas, and publishing **no
  re-identification recipe** for real people.
- **Honest limits.** Benchmark numbers are our own measurements on a small synthetic corpus
  — **not** a HIPAA/GDPR/152-ФЗ anonymisation certificate and not clinical validation. Green
  output still needs human review before any cloud use. See [`DISCLAIMER.md`](https://github.com/glebis/confide/blob/main/DISCLAIMER.md).

## Contributing

CONFIDE is a **community / citizen-science** project, built by **volunteers**, not a funded
lab — scrutiny, corrections, and especially **annotation help** are what make it
trustworthy. The gold standard needs independent human annotators (see the bilingual
[`docs/CALL-FOR-VOLUNTEERS.md`](https://github.com/glebis/confide/blob/main/docs/CALL-FOR-VOLUNTEERS.md) and the turnkey tooling:
`tools/annotator.html` + `docs/ANNOTATION-CODEBOOK.md`). Start at
[`CONTRIBUTING.md`](https://github.com/glebis/confide/blob/main/CONTRIBUTING.md).

## Reproducibility & honest reporting

Pinned environment + Docker (`Dockerfile`, `requirements.lock`), an append-only
run registry (`caches/runs/`), a CI artifact stale-check, and full docs:
`docs/REPRODUCIBILITY.md`, `docs/DATASHEET.md`, `docs/EXPLAINER.md`.

A benchmark is only as trustworthy as its reporting choices are explicit.
[`docs/REPORTING.md`](https://github.com/glebis/confide/blob/main/docs/REPORTING.md) documents exactly what CONFIDE puts in the headline
and what it leaves out, and why — recall-led (a missed leak is the real failure), no raw
real data, the OPF privacy filter kept as a lesson rather than a recommendation, and no
re-identification recipe.

## Documentation map

| Doc | What it answers |
|---|---|
| **Method & results** | |
| [`docs/REPORTING.md`](https://github.com/glebis/confide/blob/main/docs/REPORTING.md) | What the benchmark includes/omits, and why (recall-led, no raw data, no re-id recipe). |
| [`docs/RESEARCH-FINDINGS.md`](https://github.com/glebis/confide/blob/main/docs/RESEARCH-FINDINGS.md) | Deep-research positioning vs prior de-id benchmarks, methods, and datasets (needs-verification). |
| [`docs/BENCHMARK.md`](https://github.com/glebis/confide/blob/main/docs/BENCHMARK.md) | The full layered-detector ablation results and scoring method. |
| [`results/CONFIDE-RED-RESULTS.md`](https://github.com/glebis/confide/blob/main/results/CONFIDE-RED-RESULTS.md) | Red-team re-identification results (inference / singling-out / linkability). |
| **Data** | |
| [`docs/DATASHEET.md`](https://github.com/glebis/confide/blob/main/docs/DATASHEET.md) | Datasheet / data statement: provenance, composition, limits of the synthetic corpus. |
| [`docs/DATASETS.md`](https://github.com/glebis/confide/blob/main/docs/DATASETS.md) | Public datasets to extend the benchmark, fetched via the CLI. |
| **Severity & privacy** | |
| [`docs/HARM-TAXONOMY.md`](https://github.com/glebis/confide/blob/main/docs/HARM-TAXONOMY.md) | Why harm ≠ identifier-strength, and how harm-weighted recall is computed. |
| [`docs/ETHICS.md`](https://github.com/glebis/confide/blob/main/docs/ETHICS.md) | Ethics statement and responsible-use policy (ACL / NeurIPS / Menlo / Belmont norms). |
| [`docs/ISOLATION.md`](https://github.com/glebis/confide/blob/main/docs/ISOLATION.md) | Red/green data flow, no-network containers, macOS VMs, sops/age encryption. |
| [`docs/THREE-LOCKS.md`](https://github.com/glebis/confide/blob/main/docs/THREE-LOCKS.md) | Device + encrypted store + per-file isolation, with a storage checklist for real data. |
| **Reproducibility** | |
| [`docs/REPRODUCIBILITY.md`](https://github.com/glebis/confide/blob/main/docs/REPRODUCIBILITY.md) | Keeping the benchmark comparable over time; versioning, re-run policy, cost. |
| [`docs/SOURCES.md`](https://github.com/glebis/confide/blob/main/docs/SOURCES.md) | Primary/near-primary sources checked for publishable methodology claims. |
| [`requirements.lock`](https://github.com/glebis/confide/blob/main/requirements.lock) | Pinned dependencies for a deterministic environment. |
| [`Dockerfile`](https://github.com/glebis/confide/blob/main/Dockerfile) / [`run-benchmark.sh`](https://github.com/glebis/confide/blob/main/run-benchmark.sh) | Containerised, one-command benchmark run. |
| **Tools & glossary** | |
| [`docs/TOOLS.md`](https://github.com/glebis/confide/blob/main/docs/TOOLS.md) | Every external tool CONFIDE uses — what it does, its role, link, and license. |
| [`docs/GLOSSARY.md`](https://github.com/glebis/confide/blob/main/docs/GLOSSARY.md) | Bilingual EN↔RU glossary with plain-language explanations (PII/ПДн, de-id, κ, …). |
| **Plain-language** | |
| [`docs/EXPLAINER.md`](https://github.com/glebis/confide/blob/main/docs/EXPLAINER.md) | ELI5 → ELI14 explainer plus ready-to-paste blurbs for non-specialists. |

> ⚠️ **Provenance, stated precisely.** Every **therapy/coaching transcript** in this
> repository (the RU and EN-synth sessions) is **fully synthetic** — fictional clients,
> invented identifiers; no real client data ever enters it and none must. The one
> exception is **EN-real**, a small slice of the public `ai4privacy/pii-masking-300k`
> benchmark: that is **generic, non-therapy, non-clinical** PII text used only as an
> **external anchor** for the EN detectors. It contains **no real therapy/clinical data**,
> but it is *not* "synthetic" the way the therapy corpus is — it is real generic PII from a
> public dataset. **EN-real source text is NOT redistributed by this repo:** ai4privacy's
> license restricts redistribution, so the committed gold ships only **span offsets + the
> gold values + a per-document `text_sha256` and `text_len`** — never the source documents.
> To run EN-real, fetch the text yourself under ai4privacy's own license:
> `python -m confide_eval.data.fetch_ai4privacy` (needs `pip install datasets`). That
> re-downloads ai4privacy, sha256-verifies the 15 documents, and writes a local, gitignored
> `data/sessions-en/pii-eval-ai4privacy.local.jsonl` that the scorer picks up automatically.
> Without it, EN-real is skipped gracefully; RU / EN-synth are unaffected. CONFIDE-Red attacks run
> only against the fabricated therapy personas. Benchmark performance is **not** HIPAA or
> GDPR anonymisation certification.

## License & citation

- **Code** — MIT. **Data & docs** (the synthetic corpora, gold, and documentation) —
  Creative Commons Attribution 4.0 (CC-BY-4.0). See [`LICENSE`](https://github.com/glebis/confide/blob/main/LICENSE). Use it, fork it,
  improve it; please credit and keep the synthetic-data notices intact.
- **The one external slice** — EN-real comes from `ai4privacy/pii-masking-300k` and is
  carried under *that* dataset's own license (see the provenance note above), not CONFIDE's.
  Its **source text is not redistributed**; the repo ships span offsets + sha256 only, and
  `python -m confide_eval.data.fetch_ai4privacy` reconstructs it locally under ai4privacy's license.
- **Citing CONFIDE** — until a paper exists, cite the repository: *Gleb Kalinin and CONFIDE
  contributors, "CONFIDE: a therapy-transcript de-identification benchmark and red team,"
  2026, https://github.com/glebis/confide*. It is research-grade, **not** peer-reviewed; cite
  it as a tool and a measurement, not as a compliance guarantee.

CONFIDE grew out of the *Psychodemia · AI & Mental Health* masterclass (31 May 2026).
