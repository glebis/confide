#!/usr/bin/env python3
"""P1 axes: top-k re-identification attack + downstream clinical-utility.

Upgrades the basic reconstruct_attack.py per the de-id literature (Staab et al.
attribute inference; Tau-Eval task-sensitive utility; RAT-Bench attacker success):

  PRIVACY — top-k inference attack with a FIXED, declared attack budget.
    For each client, redact all sessions with the default stack (merged mask),
    give the redacted text to the qwen attacker, and ask for the TOP-3 ranked
    guesses per quasi-attribute. Score top-1 (rank-1 correct) and top-3 (any of
    3 correct) against the known synthetic profile. Report a residual-risk class.

  UTILITY — downstream task preservation (Tau-Eval style). Run the SAME clinical
    extraction (cognitive-distortion typing) on the ORIGINAL vs the REDACTED
    transcript and measure how much of the clinical signal survives. De-id is
    only useful if the therapy content it leaves behind still supports analysis.
    Also reports char-level non-PII preservation (the complement of over-redaction).

Attack budget (declared, per RAT-Bench norms): model=qwen2.5:3b, temperature=0.4,
1 call/client, top-3 candidates/attribute, attacker background knowledge = the
redacted transcript only (no external lookup). A frontier attacker is a strict
upper bound on what this lower-bound local model recovers.

Outputs privacy-utility-RESULTS.md + privacy-utility-results.json.
Requires the ru detector caches (run_detectors.py) and Ollama up.
"""
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "detector-cache")
GOLD = os.path.join(HERE, "..", "sessions-ru", "pii-eval-ru.jsonl")
DEFAULT_COMBO = ["natasha", "regex", "ollama"]
MODEL = "qwen2.5:3b"
ATTACK_TEMP = 0.4
TOPK = 3

TRUTH = {
    "a": {"profession": ["маркетолог"], "employer": ["яндекс"], "city": ["калуга"],
          "age": ["34", "тридцать четыре"], "medication": ["сертралин"]},
    "b": {"profession": ["программист"], "employer": ["контур"], "city": ["кострома"],
          "age": ["41", "сорок один"], "medication": ["флуоксетин"]},
}
# Canonical distortion vocabulary for the downstream-utility task (CBT).
DISTORTIONS = ["катастрофизация", "чтение мыслей", "сверхобобщение",
               "долженствование", "обесценивание", "дихотомическое",
               "навешивание ярлыков", "эмоциональное обоснование"]


def load_cache(det):
    p = os.path.join(CACHE, f"ru.{det}.jsonl")
    return {json.loads(l)["doc_id"]: json.loads(l)["spans"] for l in open(p, encoding="utf-8")}


def merge_intervals(spans):
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
    spans = merge_intervals(spans)
    out, last = [], 0
    for s in spans:
        out.append(text[last:s["start"]])
        out.append(f"<{s['type'].upper()}>")
        last = s["end"]
    out.append(text[last:])
    return "".join(out)


def ollama_json(prompt, temperature=0.0, num_predict=512):
    payload = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                          "stream": False, "options": {"temperature": temperature,
                                                       "num_predict": num_predict}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/chat", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        out = json.loads(resp.read())["message"]["content"]
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.DOTALL)
    m = re.search(r"[\{\[].*[\}\]]", out, re.DOTALL)
    if not m:
        return None
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return None


def topk_hit(candidates, truths):
    """candidates: list (ranked) of guess strings. Returns (top1, topk) bool."""
    if not isinstance(candidates, list):
        candidates = [candidates]
    norm = [str(c).lower() for c in candidates if c]
    def is_hit(c):
        return any(t in c for t in truths)
    top1 = bool(norm) and is_hit(norm[0])
    topk = any(is_hit(c) for c in norm[:TOPK])
    return top1, topk


def run_attack(redacted_text):
    prompt = ("You are a privacy auditor. The therapy transcript below has identifiers "
              "replaced by <TAGS>. From the REMAINING context only, give your TOP-3 ranked "
              "guesses for each attribute (most likely first). Return ONLY JSON: "
              '{"profession":["",""],"employer":["",""],"city":["",""],"age":["",""],"medication":["",""]}. '
              "Use [] if unknown.\n\n" + redacted_text[:12000])
    return ollama_json(prompt, temperature=ATTACK_TEMP) or {}


def extract_distortions(text, tag):
    prompt = ("Прочитай фрагмент терапевтической сессии. Перечисли когнитивные искажения "
              "клиента из списка: " + ", ".join(DISTORTIONS) + ". Верни ТОЛЬКО JSON-массив "
              'строк (типы искажений), напр. ["катастрофизация","чтение мыслей"]. '
              "Без пояснений.\n\nТекст:\n" + text[:9000])
    r = ollama_json(prompt, temperature=0.0)
    if not isinstance(r, list):
        return set()
    out = set()
    for item in r:
        s = str(item).lower()
        for d in DISTORTIONS:
            if d in s or s in d:
                out.add(d)
    return out


# Quasi-combination (k-anonymity) priors. DECLARED & ILLUSTRATIVE order-of-magnitude
# population fractions for Russia (~146M). Not authoritative demographics — they show
# the *method* (RAT-Bench uses US census the same way): a surviving quasi combination
# multiplies down the expected matching population; if it drops below 1, the residual
# text singles the person out even with every direct identifier masked.
RU_POP = 146_000_000
PRIORS = {  # entity_id -> fraction of the population matching that value
    "a-kaluga": 330_000 / RU_POP, "a-yandex": 25_000 / RU_POP,
    "a-profession": 0.006, "a-age": 1 / 70, "a-sertraline": 0.004,
    "b-kostroma": 270_000 / RU_POP, "b-moscow": 13_000_000 / RU_POP,
    "b-kontur": 10_000 / RU_POP, "b-zavolzhsky": 90_000 / RU_POP,
    "b-profession": 0.02, "b-age": 1 / 70, "b-fluoxetine": 0.004,
}


def quasi_combination(gold, caches):
    """For each client: which quasi entities SURVIVE the default mask, and what is the
    expected matching population of their combination (k-anonymity-style singling-out)."""
    surv = {}
    for r in gold:
        preds = merge_intervals(sum((caches[d].get(r["doc_id"], []) for d in DEFAULT_COMBO), []))
        for s in r["spans"]:
            if s["identifier_class"] != "quasi":
                continue
            masked = any(p["start"] < s["end"] and s["start"] < p["end"] for p in preds)
            e = surv.setdefault(r["client"], {}).setdefault(s["entity_id"],
                                {"type": s["type"], "masked": True})
            if not masked:
                e["masked"] = False
    out = {}
    for cl, ents in surv.items():
        survivors = {eid: e for eid, e in ents.items() if not e["masked"]}
        frac = 1.0
        used = []
        for eid in survivors:
            if eid in PRIORS:
                frac *= PRIORS[eid]
                used.append((eid, survivors[eid]["type"]))
        expected = RU_POP * frac if used else None
        out[cl] = {
            "surviving_quasi": sorted({e["type"] for e in survivors.values()}),
            "dims_used": [t for _, t in used],
            "expected_matches": round(expected, 2) if expected is not None else None,
            "singles_out": (expected is not None and expected < 1.0),
        }
    return out


def risk_class(top1, topk, survival):
    if top1 >= 2 or survival >= 0.5:
        return "HIGH"
    if topk >= 1 or survival >= 0.25:
        return "MEDIUM"
    return "LOW"


def main():
    gold = [json.loads(l) for l in open(GOLD, encoding="utf-8")]
    caches = {d: load_cache(d) for d in DEFAULT_COMBO}

    # build redacted + original per client
    by_client = {}
    for r in gold:
        spans = []
        for d in DEFAULT_COMBO:
            spans += caches[d].get(r["doc_id"], [])
        red = redact(r["text"], spans)
        by_client.setdefault(r["client"], {"orig": [], "red": []})
        by_client[r["client"]]["orig"].append(r["text"])
        by_client[r["client"]]["red"].append(red)

    results = {"attack_budget": {"model": MODEL, "temperature": ATTACK_TEMP,
                                 "calls_per_client": 1, "topk": TOPK,
                                 "background_knowledge": "redacted transcript only"},
               "privacy": {}, "utility": {},
               "quasi_combination": quasi_combination(gold, caches)}

    # ---- PRIVACY: top-k attack ----
    for cl in ["a", "b"]:
        joined = "\n\n".join(by_client[cl]["red"])[:12000]
        guess = run_attack(joined)
        attrs = {}
        n_top1 = n_topk = 0
        for attr, truths in TRUTH[cl].items():
            t1, tk = topk_hit(guess.get(attr, []), truths)
            attrs[attr] = {"top1": t1, "top3": tk, "guess": guess.get(attr, [])}
            n_top1 += int(t1); n_topk += int(tk)
        results["privacy"][cl] = {"n_attr": len(TRUTH[cl]), "top1": n_top1,
                                  "top3": n_topk, "attrs": attrs}

    # ---- UTILITY: downstream CBT-signal preservation ----
    for cl in ["a", "b"]:
        per_sess = []
        for orig, red in zip(by_client[cl]["orig"], by_client[cl]["red"]):
            d_orig = extract_distortions(orig, "orig")
            d_red = extract_distortions(red, "red")
            preserved = len(d_orig & d_red) / len(d_orig) if d_orig else None
            # char-level non-PII preservation
            red_chars = red.count("<")  # rough tag count
            per_sess.append({"orig_types": sorted(d_orig), "red_types": sorted(d_red),
                             "preserved": preserved})
        kept = [s["preserved"] for s in per_sess if s["preserved"] is not None]
        results["utility"][cl] = {
            "sessions": per_sess,
            "mean_signal_preserved": round(sum(kept) / len(kept), 3) if kept else None,
        }

    # char-level non-PII preservation (deterministic), corpus-wide
    masked_chars = total_chars = pii_chars = 0
    for r in gold:
        spans = merge_intervals(sum((caches[d].get(r["doc_id"], []) for d in DEFAULT_COMBO), []))
        gold_iv = merge_intervals([dict(s) for s in r["spans"]])
        total_chars += len(r["text"])
        for s in spans:
            masked_chars += s["end"] - s["start"]
        for g in gold_iv:
            pii_chars += g["end"] - g["start"]
    nonpii = total_chars - pii_chars
    over_masked_nonpii = max(0, masked_chars - pii_chars)
    results["utility"]["char_nonpii_preservation"] = round(1 - over_masked_nonpii / nonpii, 4) if nonpii else None

    # residual-risk class per client (needs survival from reconstruction-results if present)
    surv = {}
    rec_p = os.path.join(HERE, "reconstruction-results.json")
    if os.path.exists(rec_p):
        rec = json.load(open(rec_p, encoding="utf-8"))
        for cl in ["a", "b"]:
            surv[cl] = rec["A_quasi_survival"][cl]["survival_rate"]
    for cl in ["a", "b"]:
        p = results["privacy"][cl]
        results["privacy"][cl]["risk_class"] = risk_class(p["top1"], p["top3"], surv.get(cl, 0))

    json.dump(results, open(os.path.join(HERE, "privacy-utility-results.json"), "w"),
              ensure_ascii=False, indent=2)

    # ---- markdown ----
    md = ["# Privacy (top-k attack) & Utility (downstream task)", "",
          "Default stack: **" + "+".join(DEFAULT_COMBO) + "**. Attack budget: "
          f"`{MODEL}`, temp {ATTACK_TEMP}, 1 call/client, top-{TOPK} guesses/attribute, "
          "background knowledge = redacted transcript only. A frontier attacker is a "
          "strict upper bound on this local-model lower bound.", "",
          "## Privacy — top-k inference attack on redacted text", "",
          "| Client | top-1 hits | top-3 hits | of N | residual risk |",
          "|---|--:|--:|--:|---|"]
    for cl in ["a", "b"]:
        p = results["privacy"][cl]
        md.append(f"| {cl} | {p['top1']} | {p['top3']} | {p['n_attr']} | **{p['risk_class']}** |")
    md += ["", "Per-attribute (top-3 correct?):", "",
           "| Client | " + " | ".join(TRUTH["a"].keys()) + " |", "|---|" + "|".join("--:" for _ in TRUTH["a"]) + "|"]
    for cl in ["a", "b"]:
        cells = []
        for attr in TRUTH[cl]:
            a = results["privacy"][cl]["attrs"][attr]
            cells.append("✓" if a["top3"] else "·")
        md.append(f"| {cl} | " + " | ".join(cells) + " |")
    md += ["", "## Quasi-identifier combination (k-anonymity-style singling-out)", "",
           "Direct identifiers can be perfectly masked and a person still singled out by "
           "the *combination* of surviving quasi-identifiers. Using declared, illustrative "
           f"RU population fractions (pop ≈ {RU_POP/1e6:.0f}M; **method demo, not census**), "
           "the surviving combination multiplies down to an expected number of matching "
           "people; below 1 means singling-out.", "",
           "| Client | surviving quasi types | expected matches | singles out? |",
           "|---|---|--:|---|"]
    for cl in ("a", "b"):
        q = results["quasi_combination"].get(cl, {})
        em = q.get("expected_matches")
        md.append(f"| {cl} | {', '.join(q.get('surviving_quasi', [])) or '—'} | "
                  f"{em if em is not None else '—'} | {'**YES**' if q.get('singles_out') else 'no'} |")
    md += ["", "## Utility — downstream CBT-signal preservation (orig vs redacted)", "",
           "Does the de-identified transcript still support the clinical analysis it "
           "exists for? We extract cognitive-distortion types from the original and the "
           "redacted text and measure the fraction of original signal preserved.", "",
           "| Client | mean distortion-signal preserved |", "|---|--:|"]
    for cl in ["a", "b"]:
        v = results["utility"][cl]["mean_signal_preserved"]
        md.append(f"| {cl} | {v:.0%} |" if v is not None else f"| {cl} | n/a |")
    cnp = results["utility"]["char_nonpii_preservation"]
    md += ["", f"**Char-level non-PII preservation:** {cnp:.1%} of non-PII text survives "
           "redaction (the deterministic utility floor; complement of over-redaction).", "",
           "_Privacy↑ and utility↑ are in tension: the same masking that lowers attacker "
           "success also risks erasing clinical signal. The default stack is tuned for "
           "recall (privacy); this table is the cost side._"]
    open(os.path.join(HERE, "privacy-utility-RESULTS.md"), "w").write("\n".join(md) + "\n")

    print("[pu] privacy top1/top3:", {c: (results["privacy"][c]["top1"], results["privacy"][c]["top3"],
                                          results["privacy"][c]["risk_class"]) for c in ["a", "b"]})
    print("[pu] utility signal-preserved:", {c: results["utility"][c]["mean_signal_preserved"] for c in ["a", "b"]})
    print("[pu] char non-PII preservation:", cnp)
    print("[pu] wrote privacy-utility-RESULTS.md + .json")


if __name__ == "__main__":
    main()
