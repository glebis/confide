# Disclaimer & Status

**Read this first.** PsychoPII is a **citizen-science** project: an open de-identification
benchmark built and maintained by **volunteers**, not a funded research group or a
commercial vendor. It is offered in the spirit of open, reproducible, community-reviewed
work — useful, honestly-scoped, and improvable by anyone.

## Not scientifically validated

- This is **research-grade exploratory code and synthetic data**, **not** a peer-reviewed
  publication, **not** clinically validated, and **not** a certified product.
- Numbers are **our own measurements** on a **small, synthetic** dataset and should be read
  as **directional**, not authoritative. Each miss can move a per-type metric several points.
- Methods draw on published frameworks (TAB, i2b2/n2c2, RAT-Bench, Tau-Eval, Staab et al.),
  but our application of them has **not** been independently reviewed. Several cited works
  are **2025–2026 preprints**, flagged as such and pending verification.

## Not compliance, not clinical advice

- Passing this benchmark is **not** HIPAA Safe-Harbor / Expert-Determination compliance,
  and **not** GDPR anonymisation. GDPR identifiability is context-dependent; pseudonymised
  data can remain personal data.
- Nothing here is medical, legal, or clinical advice. De-identification tools — including
  this one — **miss things**; the benchmark itself shows ~a quarter to a third of
  quasi-identifiers survive automatic redaction. **Always do a human review** before any
  real transcript leaves a local machine.

## Built by volunteers

- Contributors are not warranting fitness for any purpose. Code is provided **as is**,
  without warranty, to the extent permitted by law (see `LICENSE`).
- Because it's volunteer-built, **scrutiny is the feature**: corrections, adversarial
  findings, and reproductions are welcome and encouraged (`CONTRIBUTING.md`).

## Data & ethics

- All shipped transcripts are **synthetic and fictional** — no real patients. See
  `docs/DATASHEET.md` (provenance) and `docs/ETHICS.md` (ethics statement, dual-use, and
  the strict conditions for any future use of real session data).

## How to cite (if you must)

> PsychoPII: a community/citizen-science synthetic benchmark for bilingual (RU/EN)
> psychotherapy-transcript de-identification. Volunteer-built, not peer-reviewed.
> Treat results as directional. See repository for methods, datasheet, ethics, and limits.

If you use it, please also state these limitations alongside any numbers you report.
