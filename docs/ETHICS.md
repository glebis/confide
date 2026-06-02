# Ethics Statement & Responsible-Use Policy — CONFIDE-Bench

For inclusion in any publication, repository, or release of the **CONFIDE-Bench**
de-identification benchmark. Written to the norms of the **ACL Ethics Policy**, the
**NeurIPS broader-impact / ethics** guidance, the **Menlo Report** (ethical principles
for security/ICT research), and the **Belmont Report** principles (respect for persons,
beneficence, justice). Pairs with `DATASHEET.md` (provenance) and `BENCHMARK.md`
(method).

---

## 1. Data and human subjects

- **No real patients; no real *therapy/clinical* data.** Every Russian and
  English-*synthetic* **therapy transcript** is **fictional**, authored as masterclass demo
  material. The "clients" (Марина, Игорь) and all embedded identifiers (names, phones,
  emails, policy/SNILS/INN numbers, medications, employers) are invented. The one piece of
  non-synthetic data is the **EN-real** slice: a small sample of the public
  `ai4privacy/pii-masking-300k` benchmark — **generic, non-therapy, non-clinical** PII text
  used only as an **external anchor** for the EN detectors. It carries **no real
  therapy/clinical records**, but to be exact it is *not* synthetic the way the therapy
  corpus is — it is real generic PII from a third-party public dataset, used unmodified
  under that dataset's license. No real personal *session* data is collected or released.
- **No human-subjects research.** Because no real person's data is collected, processed,
  or released, this work does not constitute human-subjects research and required no IRB
  review. Were real session data ever introduced (see §5), that determination changes.
- **No deception, no participants.** The "client" personas are narrative scaffolding,
  not simulations of identifiable individuals.

## 2. Dual-use and the re-identification component

A de-identification benchmark that includes **re-identification / inference attacks**
is inherently dual-use: the same measurements that help build safer anonymizers could,
in principle, guide an attacker.

- We mitigate this by running every attack **only against synthetic data** — there is no
  real person to re-identify, and the attack recovers invented attributes of fictional
  personas.
- The k-anonymity "singling-out" estimates use **declared, illustrative population
  priors** (clearly labelled, not real census linkage) to demonstrate *method*, not to
  target anyone.
- We **publish no novel attack technique**; the inference attack is a standard,
  literature-aligned probe (Staab et al.; RAT-Bench) used as a *defensive* measurement —
  to show that removing direct identifiers is necessary but not sufficient.
- Net effect: the benchmark's disclosure value (teaching clinicians and builders that
  quasi-identifiers survive) **substantially outweighs** its marginal uplift to a
  hypothetical attacker, who would gain nothing actionable from fictional profiles.

## 3. Intended use and limits

- **Intended:** comparing de-identification tools/layers; teaching; methodology research;
  informing safer, **local-first** handling of sensitive transcripts.
- **Not intended / prohibited:** clinical decision-making; treating synthetic results as
  guarantees on real data; using the attack components against real people; presenting
  benchmark performance as legal anonymisation.
- **Explicitly not a compliance instrument.** Passing CONFIDE-Bench is **not** HIPAA
  Safe-Harbor / Expert-Determination compliance, nor GDPR anonymisation. GDPR
  identifiability is context-dependent and pseudonymised data can remain personal data
  (EDPB). Any production use requires independent legal/clinical assessment.

## 4. Beneficence and broader impact

- **Intended benefit:** therapists and researchers increasingly want AI assistance with
  session material — the most sensitive text that exists. By quantifying *what survives*
  anonymization and *whether clinical utility is preserved*, CONFIDE-Bench pushes toward
  handling that protects client privacy **before** any transcript leaves a local machine.
- **Risk of misuse / over-trust:** a benchmark "score" can create false confidence. We
  counter this by headlining recall (a miss is a leak), reporting residual
  re-identification risk as a first-class result, and stating limits plainly.
- **Fairness/representation:** the synthetic personas are narrow (two professionals); the
  benchmark does not represent the diversity of real clients, dialects, or settings, and
  must not be read as doing so.

## 5. Conditions for any future use of real session data

CONFIDE-Bench is synthetic by design. If the harness is ever pointed at **real** therapy or
coaching sessions (a stated future direction), the following are **mandatory**, not
optional:

- **Informed consent** from every person whose data appears — including, critically,
  *clients of a therapist-author* (third parties who did not consent simply because the
  clinician did). Therapist-side sessions are **out of scope** absent explicit, documented
  client consent; self-as-client and own-coaching data are the consent-clean path.
- **Ethics / IRB review** and a Data Use Agreement appropriate to jurisdiction
  (cf. MIMIC/PhysioNet norms).
- **No re-identification** clause; **local-only** processing (no cloud egress of
  un-reviewed PII); secure storage; right to withdrawal.
- Treat the measured **quasi-identifier survival** as a gate: do not export a transcript
  for cloud analysis until residual risk is assessed and accepted.

## 6. Reproducibility and honesty

- All metrics are our own measurements; **vendor/model-card claims are reported
  separately** and never mixed into results.
- Gold labels are validated against an **independent annotator** (IAA), with known
  blind spots disclosed and adjudicated rather than hidden.
- Small-N and synthetic-only limitations are stated wherever numbers appear; per-type
  figures are explicitly directional.
- Cited 2025–2026 preprints are flagged as such; claims are verified before publication.

---

*Suggested paper "Ethics Statement" (≤150 words):*

> All **therapy transcripts** in CONFIDE-Bench are fully synthetic and fictional; no real
> patient data, clinical records, or human subjects are involved, so the work required no
> IRB review. (The only non-synthetic data is a small slice of the public
> `ai4privacy/pii-masking-300k` benchmark — generic, non-therapy PII used solely as an
> external EN detector anchor, containing no clinical information.) The benchmark includes re-identification/inference probes, which are run
> **only** against invented personas and recover only fabricated attributes; we publish
> no novel attack and use these measurements defensively, to show that removing direct
> identifiers leaves quasi-identifiers exploitable. Benchmark performance is **not** a
> legal anonymisation guarantee (HIPAA/GDPR). We report recall-first metrics (a missed
> identifier is a privacy breach), disclose gold-standard limitations via independent
> inter-annotator agreement, and separate our measurements from vendor claims. Any future
> application to real session data is conditioned on informed consent (including
> third-party clients), ethics review, local-only processing, and a no-re-identification
> commitment.
