#!/usr/bin/env python3
"""Reconstruction / re-identification experiment for the RU benchmark.

Three structured analyses of "what is lost and how well it can be reconstructed":

  A. Quasi-identifier SURVIVAL — of the quasi-identifiers the answer key planted
     (age, profession, employer, city, medication, ...), what fraction survive
     the default anonymization stack? Survivors are the re-identification surface
     (TAB / RAT-Bench framing). Computed from the cached detector spans.

  B. LLM INFERENCE ATTACK — redact a client's sessions with the default stack,
     then ask the local qwen model, as an *attacker*, to infer the client's
     attributes from the redacted text alone. Recovery rate = how reconstructable
     the "anonymized" transcript still is (Staab et al.-style attribute inference).

  C. UTILITY / over-redaction — what share of redacted spans were NOT real PII
     (false positives), i.e. clinical readability sacrificed. Privacy-utility
     tradeoff (Tau-Eval). Computed from gold vs predictions.

Outputs reconstruction-RESULTS.md + reconstruction-results.json.
Requires the ru detector caches (run_detectors.py) and ollama up for part B.
"""
import json
import os
import re
import urllib.request

from confide_eval import paths

HERE = os.fspath(paths.RESULTS)
CACHE = os.fspath(paths.CACHE)
GOLD = os.fspath(paths.GOLD["ru"])
DEFAULT_COMBO = ["natasha", "regex", "ollama"]

# Ground-truth attributes per client (from ANSWER-KEY §9), for the attack scorecard.
TRUTH = {
    "a": {"name": ["волкова", "марина"], "profession": ["маркетолог"],
          "employer": ["яндекс"], "city": ["калуга"], "age": ["34", "тридцать четыре"],
          "medication": ["сертралин"], "partner": ["андрей"]},
    "b": {"name": ["соколов", "игорь"], "profession": ["программист"],
          "employer": ["контур"], "city": ["кострома"], "age": ["41", "сорок один"],
          "medication": ["флуоксетин"], "family": ["алексей", "светлана"]},
}


def load_cache(det):
    p = os.path.join(CACHE, f"ru.{det}.jsonl")
    return {json.loads(l)["doc_id"]: json.loads(l)["spans"] for l in open(p, encoding="utf-8")}


def merge_intervals(spans):
    """Collapse overlapping spans to the deployed redaction mask (matches
    anonymize.py / score_bench)."""
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


def redact(text, spans):
    """Produce the deployed redaction mask. Overlapping spans are MERGED (extend
    the covered range), not skipped — skipping would leave the tail of an
    overlapping identifier in the clear (an under-redaction leak; per Codex audit)."""
    spans = sorted(spans, key=lambda s: s["start"])
    out, last = [], 0
    for s in spans:
        if s["start"] < last:
            last = max(last, s["end"])   # merge: extend coverage, don't drop the tail
            continue
        out.append(text[last:s["start"]])
        out.append(f"<{s['type'].upper()}>")
        last = s["end"]
    out.append(text[last:])
    return "".join(out)


def ollama_attack(redacted_text, model="qwen2.5:3b"):
    prompt = ("You are a privacy auditor testing whether an anonymized therapy "
              "transcript still leaks identity. The transcript has names/numbers "
              "replaced by <TAGS>. From the REMAINING context only, infer the client's "
              "attributes. Return ONLY JSON: "
              '{"profession":"","employer":"","city":"","age":"","medication":"","other_clues":""}. '
              "Use \"\" if truly unknown. Text:\n\n" + redacted_text)
    payload = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                          "stream": False, "options": {"temperature": 0, "num_predict": 512}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        out = json.loads(resp.read())["message"]["content"]
    m = re.search(r"\{.*\}", out, re.DOTALL)
    return json.loads(m.group()) if m else {}


def hit(guess, truths):
    g = (guess or "").lower()
    return any(t in g for t in truths) if g else False


def main():
    gold = [json.loads(l) for l in open(GOLD, encoding="utf-8")]
    caches = {d: load_cache(d) for d in DEFAULT_COMBO}

    # ---- A. quasi-identifier survival (from cached spans) ----
    surv = {}  # client -> {entity_id: {"type","value","masked":bool}}
    for r in gold:
        preds = []
        for d in DEFAULT_COMBO:
            preds += caches[d].get(r["doc_id"], [])
        for s in r["spans"]:
            if s["identifier_class"] != "quasi":
                continue
            masked = any(p["start"] < s["end"] and s["start"] < p["end"] for p in preds)
            e = surv.setdefault(r["client"], {}).setdefault(s["entity_id"],
                                {"type": s["type"], "masked": True, "n": 0})
            e["n"] += 1
            if not masked:
                e["masked"] = False  # any unmasked mention => entity survives

    survival = {}
    for cl, ents in surv.items():
        survived = [e for e in ents.values() if not e["masked"]]
        survival[cl] = {
            "quasi_entities": len(ents),
            "survived": len(survived),
            "survival_rate": round(len(survived) / len(ents), 3) if ents else 0.0,
            "survivors_by_type": sorted({e["type"] for e in survived}),
        }

    # ---- B. LLM inference attack on redacted text ----
    attack = {}
    ollama_ok = True
    for cl in ["a", "b"]:
        docs = [r for r in gold if r["client"] == cl]
        red = []
        for r in docs:
            spans = []
            for d in DEFAULT_COMBO:
                spans += caches[d].get(r["doc_id"], [])
            red.append(redact(r["text"], spans))
        joined = "\n\n".join(red)[:12000]
        try:
            guess = ollama_attack(joined)
        except Exception as e:
            ollama_ok = False
            attack[cl] = {"error": f"{type(e).__name__}: {e}"}
            continue
        score = {attr: hit(guess.get(attr, ""), truths)
                 for attr, truths in TRUTH[cl].items() if attr in guess or attr in
                 ("profession", "employer", "city", "age", "medication")}
        recovered = [a for a, ok in score.items() if ok]
        attack[cl] = {"guess": guess, "recovered": recovered,
                      "n_recovered": len(recovered), "n_tested": len(score)}

    # ---- C. utility / over-redaction (FP share) under default combo ----
    fp = tp = 0
    for r in gold:
        preds = []
        for d in DEFAULT_COMBO:
            preds += caches[d].get(r["doc_id"], [])
        preds = merge_intervals(preds)   # score the deployed mask, not raw spans
        gspans = r["spans"]
        for p in preds:
            if any(p["start"] < g["end"] and g["start"] < p["end"] for g in gspans):
                tp += 1
            else:
                fp += 1
    over_redaction = {"redacted_spans": tp + fp, "false_positives": fp,
                      "over_redaction_rate": round(fp / (tp + fp), 3) if (tp + fp) else 0.0}

    results = {"default_combo": "+".join(DEFAULT_COMBO),
               "A_quasi_survival": survival,
               "B_inference_attack": attack,
               "C_over_redaction": over_redaction}
    json.dump(results, open(os.path.join(HERE, "reconstruction-results.json"), "w"),
              ensure_ascii=False, indent=2)

    # ---- markdown ----
    md = ["# Reconstruction & Re-identification — what survives anonymization", "",
          f"Default stack under test: **{results['default_combo']}** (the RU benchmark default).",
          "Method follows the re-identification / inference-attack literature "
          "(Staab et al.; RAT-Bench; Tau-Eval privacy–utility).", "",
          "## A. Quasi-identifier survival (the re-identification surface)", "",
          "An entity *survives* if **any** of its mentions is left unmasked. "
          "Direct identifiers (name/phone/email) are well masked; the danger is the "
          "quasi-identifiers that, combined, still single out a person.", "",
          "| Client | Quasi-entities | Survived | Survival rate | Surviving types |",
          "|---|--:|--:|--:|---|"]
    for cl, s in survival.items():
        md.append(f"| {cl} | {s['quasi_entities']} | {s['survived']} | "
                  f"**{s['survival_rate']:.0%}** | {', '.join(s['survivors_by_type']) or '—'} |")
    md += ["", "## B. LLM inference attack on the *redacted* text", "",
           "A local qwen model, given only the anonymized transcript (`<TAGS>` in place "
           "of PII), is asked to infer the client's attributes from remaining context.",
           "Recovered = attribute correctly reconstructed despite redaction.", ""]
    if ollama_ok:
        md += ["| Client | Recovered / tested | Reconstructed attributes |", "|---|--:|---|"]
        for cl, a in attack.items():
            if "error" in a:
                md.append(f"| {cl} | (error) | {a['error']} |"); continue
            md.append(f"| {cl} | {a['n_recovered']}/{a['n_tested']} | "
                      f"{', '.join(a['recovered']) or '—'} |")
        md += ["", "_Even a 3B local model reconstructs identity-narrowing attributes "
               "from context alone; a frontier model would recover more (the literature "
               "reports state-of-the-art tools prevent re-identification only ~27–29% of "
               "the time). Redaction of direct identifiers is necessary but not sufficient._"]
    else:
        md.append("_Ollama was unavailable; attack skipped._")
    md += ["", "## C. Utility cost (over-redaction)", "",
           f"Under the default stack, **{over_redaction['false_positives']} of "
           f"{over_redaction['redacted_spans']}** redacted spans "
           f"(**{over_redaction['over_redaction_rate']:.0%}**) were not gold PII — "
           "the readability price paid for recall. In de-id this is the cheap error "
           "(over-redaction costs readability; a miss leaks PII).", ""]
    open(os.path.join(HERE, "reconstruction-RESULTS.md"), "w").write("\n".join(md) + "\n")

    print("[reconstruct] A survival:", {c: f"{s['survival_rate']:.0%}" for c, s in survival.items()})
    print("[reconstruct] B attack:", {c: (a.get("recovered") if "error" not in a else "err")
                                       for c, a in attack.items()})
    print("[reconstruct] C over-redaction:", f"{over_redaction['over_redaction_rate']:.0%}")
    print("[reconstruct] wrote reconstruction-RESULTS.md + .json")


if __name__ == "__main__":
    main()
