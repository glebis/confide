#!/usr/bin/env python3
"""Shared singling-out / k-anonymity estimator for CONFIDE.

ONE survivor-detection method (entity-aware, gold + detector caches — deterministic,
no LLM) and ONE prior table, imported by BOTH confide_red.py and
privacy_utility_eval.py so they can never again report different expected-match
counts for the same client (audit bug B1: 104.3 vs 3504).

================================  HONESTY LABEL  ================================
These expected-match numbers are **ILLUSTRATIVE — a methodological demonstration**
of how a combination of surviving quasi-identifiers is assessed for singling-out
(GDPR Art-29 / k-anonymity style; RAT-Bench applies US census the same way). They
are NOT a precise re-identification probability for these fabricated personas:

  * The personas are synthetic, so no real population actually carries these
    value combinations — the priors are anchors, not measurements.
  * The estimate multiplies per-quasi population fractions as if the
    quasi-identifiers were **statistically independent**. Real quasi-identifiers
    are correlated (profession↔city↔age↔medication), so the naive product
    OVERSTATES uniqueness (true matching population is larger ⇒ less singled-out
    than the point estimate suggests). See `independence_caveat()`.

The defensible, load-bearing signal is the **relative ranking** (which clients are
more exposed) and the **sensitivity verdict** (does "expected < 1" survive moving
every prior by 0.5x–2x?), NOT the exact point value.
==============================================================================="""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "detector-cache")
GOLD = os.path.join(HERE, "..", "sessions-ru", "pii-eval-ru.jsonl")
DEFAULT_COMBO = ["natasha", "regex", "ollama"]

# Russia population. Source: Rosstat resident-population estimate, ~146.0M (2021
# census / 2023 estimate). Citable, exact at this order of magnitude.
RU_POP = 146_000_000

INDEPENDENCE_CAVEAT = (
    "Naive product of per-quasi fractions assumes the quasi-identifiers are "
    "statistically independent. They are not (profession/city/age/medication "
    "correlate), so this OVERSTATES uniqueness — the real matching population is "
    "larger and the person is LESS singled out than the point estimate implies."
)


# ---------------------------------------------------------------------------
# ONE prior table. Fraction of RU_POP carrying a given quasi VALUE.
#
# SOURCING (every fraction carries a provenance tag):
#   [census]   city resident populations — Rosstat 2021 city totals (citable, exact).
#   [estimate] profession / medication / age-band shares — order-of-magnitude
#              author estimates, NOT authoritative demographics. Treated as
#              illustrative anchors and stress-tested in the sensitivity sweep.
#
# Keyed by gold entity_id so survival is entity-aware (not substring guessing).
# ---------------------------------------------------------------------------
PRIORS = {
    # --- cities: resident population / RU_POP  [census, Rosstat 2021] ---
    "a-kaluga":        330_000 / RU_POP,   # Kaluga ~332k
    "b-kostroma":      270_000 / RU_POP,   # Kostroma ~277k
    "b-ekaterinburg": 1_500_000 / RU_POP,  # Yekaterinburg ~1.49M
    "b-moscow":      13_000_000 / RU_POP,  # Moscow ~13M
    "b-zavolzhsky":     90_000 / RU_POP,   # Zavolzhsky district [estimate]
    "c-spb":          5_600_000 / RU_POP,  # St Petersburg ~5.6M
    "d-nsk":          1_600_000 / RU_POP,  # Novosibirsk ~1.63M
    "e-ekb":          1_500_000 / RU_POP,  # Yekaterinburg ~1.49M
    "f-kazan":        1_300_000 / RU_POP,  # Kazan ~1.31M

    # --- professions: share of working-age population  [estimate, ~0.5-2%] ---
    # White-collar specialisms (~0.5-1% each); two PROFESSION entities per client
    # (profession + career-level/role) are both quasi but describe ONE job, so we
    # collapse them to a single profession fraction in the estimator (see _frac).
    "a-profession": 0.006, "a-careerlevel": 1.0,   # marketer; careerlevel folded in
    "b-profession": 0.020, "b-role": 1.0,          # programmer; role folded in
    "c-profession": 0.004,                          # designer
    "d-profession": 0.010,                          # entrepreneur
    "e-profession": 0.012,                          # teacher
    "f-profession": 0.020,                          # programmer/student

    # --- age: one birth-year band  [estimate, ~1/70 of population] ---
    "a-age": 1 / 70, "b-age": 1 / 70, "c-age": 1 / 70,
    "d-age": 1 / 70, "e-age": 1 / 70, "f-age": 1 / 70,

    # --- antidepressant on a given molecule  [estimate, ~0.3-0.5%] ---
    "a-sertraline":   0.004, "b-fluoxetine":  0.004, "c-escitalopram": 0.004,
    "d-bupropion":    0.003, "e-mirtazapine": 0.003, "f-atomoxetine":  0.002,
}

# Folded-in companions: a PROFESSION sub-entity whose information is already
# captured by the primary profession fraction (prior 1.0 ⇒ no extra narrowing).
_FOLDED = {"a-careerlevel", "b-role"}


def _load_cache(det):
    p = os.path.join(CACHE, f"ru.{det}.jsonl")
    return {json.loads(l)["doc_id"]: json.loads(l)["spans"] for l in open(p, encoding="utf-8")}


def _merge(spans):
    if not spans:
        return []
    ss = sorted(spans, key=lambda s: (s["start"], -(s["end"] - s["start"])))
    out = [dict(ss[0])]
    for s in ss[1:]:
        if s["start"] < out[-1]["end"]:
            out[-1]["end"] = max(out[-1]["end"], s["end"])
        else:
            out.append(dict(s))
    return out


def surviving_quasi(combo=None):
    """Deterministic, entity-aware survivor detection from gold + detector caches.

    A gold quasi entity SURVIVES if at least one of its mentions is left unmasked
    by the merged default-combo mask. Returns {client: {entity_id: type}}.
    No LLM — caches are read-only and committed, so this is reproducible.
    """
    combo = combo or DEFAULT_COMBO
    caches = {d: _load_cache(d) for d in combo}
    gold = [json.loads(l) for l in open(GOLD, encoding="utf-8")]
    state = {}
    for r in gold:
        preds = _merge(sum((caches[d].get(r["doc_id"], []) for d in combo), []))
        for s in r["spans"]:
            if s.get("identifier_class") != "quasi":
                continue
            masked = any(p["start"] < s["end"] and s["start"] < p["end"] for p in preds)
            e = state.setdefault(r["client"], {}).setdefault(
                s["entity_id"], {"type": s["type"], "masked": True})
            if not masked:
                e["masked"] = False
    out = {}
    for cl, ents in state.items():
        out[cl] = {eid: e["type"] for eid, e in ents.items() if not e["masked"]}
    return out


def _frac(survivors, priors):
    """Multiply priors of surviving entities that have a declared prior.

    `survivors` is {entity_id: type}. Folded companions (careerlevel/role) and
    entities without a prior contribute nothing extra. Returns (frac, dims_used)
    where dims_used is the list of (entity_id, type) actually multiplied in."""
    frac, used = 1.0, []
    for eid, typ in sorted(survivors.items()):
        if eid in _FOLDED:
            continue
        if eid in priors:
            frac *= priors[eid]
            used.append((eid, typ))
    return frac, used


def singling_out(client, survivors=None, priors=None):
    """ONE estimator both scripts call. Same client ⇒ same expected_matches.

    survivors: optional {entity_id: type} for this client; if None, computed
               deterministically from gold + caches via surviving_quasi().
    Returns the canonical singling-out dict (ILLUSTRATIVE — see module docstring).
    """
    priors = priors or PRIORS
    if survivors is None:
        survivors = surviving_quasi().get(client, {})
    frac, used = _frac(survivors, priors)
    expected = round(RU_POP * frac, 1) if used else None
    return {
        "client": client,
        "surviving_quasi": sorted({t for t in survivors.values()}),
        "dims_used": [t for _, t in used],
        "dims_entities": [e for e, _ in used],
        "expected_matches": expected,
        "singles_out": expected is not None and expected < 1.0,
        "illustrative": True,
    }


def sensitivity(client, survivors=None, factors=(0.5, 2.0)):
    """Stress-test the verdict: scale EACH prior by each factor, one at a time,
    and also all-together, then report whether 'expected < 1' flips. Returns a
    table + a `verdict_robust` flag (True if the singled-out verdict never flips)."""
    if survivors is None:
        survivors = surviving_quasi().get(client, {})
    base = singling_out(client, survivors)
    base_verdict = base["singles_out"]
    rows = [("baseline", "—", base["expected_matches"], base_verdict)]
    robust = True

    # one-at-a-time: scale a single surviving entity's prior
    for eid, typ in sorted(survivors.items()):
        if eid in _FOLDED or eid not in PRIORS:
            continue
        for f in factors:
            p = dict(PRIORS)
            p[eid] = min(1.0, p[eid] * f)
            r = singling_out(client, survivors, p)
            flip = r["singles_out"] != base_verdict
            robust &= not flip
            rows.append((f"{typ}({eid})", f"x{f}", r["expected_matches"], r["singles_out"]))

    # all-together worst/best case
    for f in factors:
        p = {k: min(1.0, v * f) for k, v in PRIORS.items()}
        r = singling_out(client, survivors, p)
        flip = r["singles_out"] != base_verdict
        robust &= not flip
        rows.append(("ALL priors", f"x{f}", r["expected_matches"], r["singles_out"]))

    return {"client": client, "baseline_verdict": base_verdict,
            "verdict_robust": robust, "rows": rows}


def independence_caveat():
    return INDEPENDENCE_CAVEAT


if __name__ == "__main__":
    # selftest / demo: print the unified estimate + sensitivity for each client.
    surv = surviving_quasi()
    print("# k-anon ILLUSTRATIVE singling-out (shared estimator)\n")
    for cl in sorted(surv):
        s = singling_out(cl, surv[cl])
        print(f"client {cl}: expected_matches={s['expected_matches']} "
              f"dims={s['dims_used']} singles_out={s['singles_out']}")
    print("\n# sensitivity (does the verdict hold under 0.5x-2x prior swings?)\n")
    for cl in sorted(surv):
        sw = sensitivity(cl, surv[cl])
        print(f"client {cl}: baseline_verdict={sw['baseline_verdict']} "
              f"verdict_robust={sw['verdict_robust']}")
    print("\ncaveat:", independence_caveat())
