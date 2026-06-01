#!/usr/bin/env python3
"""Inter-annotator agreement (IAA) on a seed set — addresses the circular-gold
critique (Codex + research P0: the gold is pattern-derived from the answer keys).

Annotator 1 (A1) = the pattern-derived gold (build_ru_dataset.py).
Annotator 2 (A2) = an INDEPENDENT from-scratch annotation by a different, stronger
model (GPT-5 via Codex), given only the transcript text — /tmp/annotator2.json,
a {doc_id: [{text,type}]} object. A2's strings are located in the transcript to
get char spans.

Agreement is reported two ways:
  - span-level precision/recall/F1 of A2 vs A1 (overlap match) — the usual proxy
    for span-annotation IAA when there is no shared token layer;
  - character-level Cohen's kappa on the binary "is-PII char" labelling.

Adjudication lists A2-only spans (candidate GOLD BLIND SPOTS) and A1-only spans
(A2 misses), so a human can reconcile them into an adjudicated gold.

Output: IAA-RESULTS.md + iaa-results.json.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
GOLD = os.path.join(HERE, "..", "sessions-ru", "pii-eval-ru.jsonl")
A2_PATH = os.path.join(HERE, "iaa-annotator2-seed.json")  # GPT-5/Codex independent annotation (committed for reproducibility)
SEED = ["ru-a-s01", "ru-b-s01"]


def locate(text, value):
    """All char spans where `value` occurs (case-insensitive)."""
    if not value or len(value) < 2:
        return []
    return [(m.start(), m.end()) for m in re.finditer(re.escape(value), text, re.IGNORECASE)]


def overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def char_mask(spans, n):
    m = bytearray(n)
    for s, e in spans:
        for i in range(max(0, s), min(n, e)):
            m[i] = 1
    return m


def cohen_kappa(m1, m2):
    n = len(m1)
    if n == 0:
        return 0.0
    both1 = sum(1 for i in range(n) if m1[i] and m2[i])
    both0 = sum(1 for i in range(n) if not m1[i] and not m2[i])
    po = (both1 + both0) / n
    p1 = sum(m1) / n
    p2 = sum(m2) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return (po - pe) / (1 - pe) if (1 - pe) else 1.0


def main():
    gold_rows = {r["doc_id"]: r for r in (json.loads(l) for l in open(GOLD, encoding="utf-8"))}
    a2 = json.load(open(A2_PATH, encoding="utf-8"))

    per_doc = {}
    tot = {"a1": 0, "a2": 0, "a2_hit": 0, "a1_hit": 0}
    kappas = []
    blind_spots, a1_only = [], []

    for doc_id in SEED:
        g = gold_rows[doc_id]
        text = g["text"]
        all_a1_spans = [(s["start"], s["end"]) for s in g["spans"]]
        # A1 ENTITIES: group gold mention-spans by entity_id (avoids per-occurrence
        # inflation — Codex audit #1). An entity is "agreed" if A2 overlaps any mention.
        a1_entities = {}
        for s in g["spans"]:
            a1_entities.setdefault(s["entity_id"], []).append((s["start"], s["end"], s["type"]))
        # A2 ITEMS: each distinct annotation, located (all occurrences) for matching only.
        a2_items = []
        for item in a2.get(doc_id, []):
            spans = locate(text, item.get("text", ""))
            if spans:
                a2_items.append({"type": item.get("type", "?"), "text": item.get("text", ""),
                                 "spans": spans})
        a2_all_spans = [sp for it in a2_items for sp in it["spans"]]

        # recall: A1 entities covered by some A2 span (entity-level, not per-mention)
        a1_hit = sum(1 for ms in a1_entities.values()
                     if any(overlaps((s, e), p) for (s, e, _t) in ms for p in a2_all_spans))
        # precision: A2 items overlapping some A1 gold span
        a2_hit = sum(1 for it in a2_items
                     if any(overlaps(sp, q) for sp in it["spans"] for q in all_a1_spans))
        # disagreements
        for it in a2_items:
            if not any(overlaps(sp, q) for sp in it["spans"] for q in all_a1_spans):
                blind_spots.append((doc_id, it["text"], it["type"]))
        for eid, ms in a1_entities.items():
            if not any(overlaps((s, e), p) for (s, e, _t) in ms for p in a2_all_spans):
                a1_only.append((doc_id, text[ms[0][0]:ms[0][1]], ms[0][2]))

        k = cohen_kappa(char_mask(all_a1_spans, len(text)),
                        char_mask(a2_all_spans, len(text)))
        kappas.append(k)
        per_doc[doc_id] = {"a1": len(a1_entities), "a2": len(a2_items),
                           "a2_hit": a2_hit, "a1_hit": a1_hit, "kappa": round(k, 3)}
        tot["a1"] += len(a1_entities); tot["a2"] += len(a2_items)
        tot["a2_hit"] += a2_hit; tot["a1_hit"] += a1_hit

    precision = tot["a2_hit"] / tot["a2"] if tot["a2"] else 0.0   # A2 items matching A1
    recall = tot["a1_hit"] / tot["a1"] if tot["a1"] else 0.0      # A1 entities A2 also marked
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    mean_kappa = sum(kappas) / len(kappas) if kappas else 0.0

    results = {"seed": SEED, "per_doc": per_doc,
               "span_agreement": {"precision": round(precision, 3), "recall": round(recall, 3),
                                  "f1": round(f1, 3)},
               "char_cohen_kappa": round(mean_kappa, 3),
               "gold_blind_spots": blind_spots, "a1_only": a1_only}
    json.dump(results, open(os.path.join(HERE, "iaa-results.json"), "w"),
              ensure_ascii=False, indent=2)

    md = ["# LLM-assisted consistency check (single second-annotator) — seed set", "",
          "**This is NOT human inter-annotator agreement.** It is an *LLM-assisted "
          "consistency check* with a single, automated second annotator (per Codex audit "
          "R4). A human multi-annotator study with adjudication is still required before "
          "any publishable agreement claim; the numbers below only flag where the "
          "pattern-derived gold and an independent LLM pass disagree.", "",
          f"Seed: {', '.join(SEED)} (the two densest sessions). **A1** = pattern-derived "
          "gold; **A2** = independent from-scratch annotation by GPT-5 (Codex), given only "
          "the transcript. This checks the gold against one independent automated annotator "
          "— the research/Codex P0 probe for the circular, pattern-derived gold.", "",
          "## Consistency (A2 vs A1)", "",
          f"- **Entity-level F1 (A2 vs A1): {f1:.3f}**  (precision {precision:.3f} = A2 items "
          f"matching gold; recall {recall:.3f} = gold *entities* A2 also marked). Entity-level "
          "(gold mentions grouped by entity_id) to avoid per-occurrence inflation.",
          f"- **Character-level Cohen's κ: {mean_kappa:.3f}**  "
          f"({'substantial' if mean_kappa>=0.6 else 'moderate' if mean_kappa>=0.4 else 'fair'} "
          "consistency vs the single LLM second-annotator — not a human-agreement κ)",
          "",
          "| Doc | A1 entities | A2 items | A2 hit | A1 hit | κ |",
          "|---|--:|--:|--:|--:|--:|"]
    for d in SEED:
        p = per_doc[d]
        md.append(f"| {d} | {p['a1']} | {p['a2']} | {p['a2_hit']} | {p['a1_hit']} | {p['kappa']} |")
    md += ["", "## Gold blind spots — A2 found, A1 (gold) missed", "",
           "Candidate additions for adjudication. Notably the spelled-out identifiers and "
           "relative dates the pattern-derived gold cannot express:", ""]
    for doc_id, txt, typ in blind_spots[:40]:
        md.append(f"- `{doc_id}` **{typ}**: {txt!r}")
    md += ["", "## A1-only — gold has, A2 missed", ""]
    for doc_id, txt, typ in a1_only[:40]:
        md.append(f"- `{doc_id}` **{typ}**: {txt!r}")
    md += ["", "## Adjudication note", "",
           "A2-only items are mostly (a) **spelled-out** phone/policy digits and "
           "(b) **relative dates** (\"прошлой неделе\", \"года три назад\") — real PII the "
           "regex/answer-key gold structurally omits. These should be adjudicated into a "
           "v2 gold (or explicitly scoped out). A1-only items are mostly morphological "
           "mentions A2 reported once. IAA here measures gold *completeness*, not just "
           "boundary agreement.", ""]
    open(os.path.join(HERE, "IAA-RESULTS.md"), "w").write("\n".join(md) + "\n")
    print(f"[iaa] span-F1={f1:.3f} (P={precision:.3f} R={recall:.3f}), char-kappa={mean_kappa:.3f}")
    print(f"[iaa] blind spots (A2-only): {len(blind_spots)}; A1-only: {len(a1_only)}")
    print(f"[iaa] wrote IAA-RESULTS.md + iaa-results.json")


if __name__ == "__main__":
    main()
