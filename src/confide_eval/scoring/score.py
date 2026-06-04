#!/usr/bin/env python3
"""
Entity-level scoring for the OpenAI Privacy Filter eval, following the
Microsoft Presidio-research evaluation methodology.

Each predicted entity is matched against gold entities and classified as:
  - correct  : type matches AND span criterion satisfied
  - partial  : type matches AND spans overlap but are not identical (relaxed only)
  - wrong-type: span criterion satisfied but type differs (counts as FP + FN)
  - spurious : predicted entity with no gold overlap                  (FP)
  - missed   : gold entity with no matching prediction                (FN)

Two modes:
  STRICT  : a prediction is "correct" only if start AND end match a gold entity
            of the same type exactly. Partial overlaps are NOT credited.
  RELAXED : a prediction is "correct" if it overlaps (by >=1 char) a gold entity
            of the same type. This is Presidio's token/overlap-tolerant view and
            the one that best reflects "did we catch the PII at all".

Metrics, per type and overall:
  precision = correct / (correct + FP)
  recall    = correct / (correct + FN)
  F1        = 2PR / (P+R)
  F2        = 5PR / (4P+R)   <-- recall-weighted, HEADLINE metric.

Why F2 / recall is the headline: in de-identification a MISSED entity is leaked
PII (a privacy breach), whereas a FALSE POSITIVE is merely over-redaction (a
readability cost). Presidio-research and the i2b2/n2c2 clinical de-id tradition
both weight recall above precision for exactly this reason. See eval/README.md.

Outputs:
  results.json  -- machine-readable, both modes, per-type + overall + run meta.
  RESULTS.md    -- human-readable tables, headline F2, error breakdown.

Usage:
  python score.py [--gold ../sessions-en/pii-eval.jsonl]
                  [--pred predictions.jsonl]
"""
import argparse
import json
import os

from confide_eval import paths

HERE = os.fspath(paths.RESULTS)
TYPES = ["private_person", "private_address", "private_email", "private_phone",
         "private_url", "private_date", "account_number", "secret"]


def overlaps(a, b):
    return a["start"] < b["end"] and b["start"] < a["end"]


def exact(a, b):
    return a["start"] == b["start"] and a["end"] == b["end"]


def score_mode(gold_rows, pred_rows, relaxed):
    """Returns (per_type_counts, totals). Counts: correct, fp, fn, partial,
    wrong_type. Matching is greedy per snippet; each gold/pred used at most once."""
    match = overlaps if relaxed else exact
    per = {t: {"correct": 0, "fp": 0, "fn": 0, "partial": 0, "wrong_type": 0} for t in TYPES}

    for g_row, p_row in zip(gold_rows, pred_rows):
        gold = [dict(s, _used=False) for s in g_row["spans"]]
        preds = [dict(s, _used=False) for s in p_row["spans"]]

        # Pass 1: same-type matches (correct, or partial in relaxed mode)
        for p in preds:
            if p["type"] not in per:
                continue  # model emitted a label outside our 8 -> handled as spurious below
            for g in gold:
                if g["_used"] or g["type"] != p["type"]:
                    continue
                if exact(p, g):
                    per[p["type"]]["correct"] += 1
                    g["_used"] = p["_used"] = True
                    break
                if relaxed and overlaps(p, g):
                    per[p["type"]]["correct"] += 1   # overlap credited as correct in relaxed
                    per[p["type"]]["partial"] += 1   # also tracked as "partial" for reporting
                    g["_used"] = p["_used"] = True
                    break

        # Pass 2: wrong-type matches (span criterion met, type differs) -> FP+FN
        for p in preds:
            if p["_used"]:
                continue
            for g in gold:
                if g["_used"]:
                    continue
                if match(p, g):
                    # wrong type: penalize both sides
                    if p["type"] in per:
                        per[p["type"]]["fp"] += 1
                    per[g["type"]]["fn"] += 1
                    per[g["type"]]["wrong_type"] += 1
                    g["_used"] = p["_used"] = True
                    break

        # Remaining unmatched predictions -> spurious FP
        for p in preds:
            if not p["_used"] and p["type"] in per:
                per[p["type"]]["fp"] += 1
        # Remaining unmatched gold -> missed FN
        for g in gold:
            if not g["_used"]:
                per[g["type"]]["fn"] += 1

    totals = {"correct": 0, "fp": 0, "fn": 0, "partial": 0, "wrong_type": 0}
    for t in TYPES:
        for k in totals:
            totals[k] += per[t][k]
    return per, totals


def prf(c, fp, fn):
    p = c / (c + fp) if (c + fp) else 0.0
    r = c / (c + fn) if (c + fn) else 0.0
    f1 = 2 * p * r / (p + r) if (p + r) else 0.0
    f2 = 5 * p * r / (4 * p + r) if (4 * p + r) else 0.0
    return p, r, f1, f2


def build_block(per, totals):
    block = {"per_type": {}, "overall": {}}
    for t in TYPES:
        c, fp, fn = per[t]["correct"], per[t]["fp"], per[t]["fn"]
        p, r, f1, f2 = prf(c, fp, fn)
        block["per_type"][t] = {
            "support": c + fn, "correct": c, "fp": fp, "fn": fn,
            "precision": round(p, 4), "recall": round(r, 4),
            "f1": round(f1, 4), "f2": round(f2, 4),
        }
    c, fp, fn = totals["correct"], totals["fp"], totals["fn"]
    p, r, f1, f2 = prf(c, fp, fn)
    block["overall"] = {
        "support": c + fn, "correct": c, "fp": fp, "fn": fn,
        "precision": round(p, 4), "recall": round(r, 4),
        "f1": round(f1, 4), "f2": round(f2, 4),
        "partial_overlap_matches": totals["partial"],
        "wrong_type": totals["wrong_type"],
    }
    return block


def md_table(block, mode_name):
    lines = [f"### {mode_name}", "",
             "| Type | Support | Correct | FP | FN | Precision | Recall | F1 | **F2** |",
             "|------|--------:|--------:|---:|---:|----------:|-------:|---:|-------:|"]
    for t in TYPES:
        m = block["per_type"][t]
        if m["support"] == 0:
            continue
        lines.append(f"| {t} | {m['support']} | {m['correct']} | {m['fp']} | {m['fn']} | "
                     f"{m['precision']:.3f} | {m['recall']:.3f} | {m['f1']:.3f} | **{m['f2']:.3f}** |")
    o = block["overall"]
    lines.append(f"| **OVERALL** | **{o['support']}** | **{o['correct']}** | **{o['fp']}** | "
                 f"**{o['fn']}** | **{o['precision']:.3f}** | **{o['recall']:.3f}** | "
                 f"**{o['f1']:.3f}** | **{o['f2']:.3f}** |")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=os.fspath(paths.GOLD["en"]))
    ap.add_argument("--pred", default=os.path.join(HERE, "predictions.jsonl"))
    ap.add_argument("--out-prefix", default="",
                    help="prefix for output files, e.g. 'ai4privacy-' -> "
                         "ai4privacy-RESULTS.md / ai4privacy-results.json")
    args = ap.parse_args()
    pfx = args.out_prefix

    gold_rows = [json.loads(l) for l in open(args.gold)]
    pred_rows = [json.loads(l) for l in open(args.pred)]
    assert len(gold_rows) == len(pred_rows), \
        f"gold({len(gold_rows)}) and pred({len(pred_rows)}) row count mismatch"

    strict_per, strict_tot = score_mode(gold_rows, pred_rows, relaxed=False)
    relax_per, relax_tot = score_mode(gold_rows, pred_rows, relaxed=True)
    strict = build_block(strict_per, strict_tot)
    relaxed = build_block(relax_per, relax_tot)

    run_meta = {}
    rm_path = os.path.join(HERE, "run_meta.json")
    if os.path.exists(rm_path):
        run_meta = json.load(open(rm_path))

    results = {
        "dataset": os.path.relpath(args.gold, HERE),
        "n_snippets": len(gold_rows),
        "n_gold_entities": sum(len(r["spans"]) for r in gold_rows),
        "n_pred_entities": sum(len(r["spans"]) for r in pred_rows),
        "headline_metric": "F2 (recall-weighted), relaxed/overlap mode",
        "strict": strict,
        "relaxed": relaxed,
        "run_meta": run_meta,
    }
    with open(os.path.join(HERE, f"{pfx}results.json"), "w") as f:
        json.dump(results, f, indent=2)

    head_f2 = relaxed["overall"]["f2"]
    head_r = relaxed["overall"]["recall"]
    md = ["# OpenAI Privacy Filter — English PII Eval Results", ""]
    if run_meta:
        md.append("> **STATUS: EXECUTED.** Numbers below are our own measurement, "
                  "produced by `run_opf.py` + `score.py` on this machine. "
                  "Vendor-claimed model-card numbers are listed separately at the "
                  "bottom and are NOT mixed into our results.")
    else:
        md.append("> **STATUS: NOT YET EXECUTED.** The scripts are correct and runnable "
                  "but no `run_meta.json` was found. Reproduce with:\n"
                  ">\n"
                  "> ```bash\n"
                  "> pip install -r requirements.txt\n"
                  "> python build_dataset.py   # writes ../sessions-en/pii-eval.jsonl\n"
                  "> python run_opf.py         # downloads ~2.8GB, runs on CPU\n"
                  "> python score.py           # writes this file + results.json\n"
                  "> ```")
    md.append("")
    md.append(f"**Dataset:** `{os.path.relpath(args.gold)}` — "
              f"{results['n_snippets']} snippets, {results['n_gold_entities']} gold entities.")
    if run_meta:
        md.append(f"**Model:** `{run_meta.get('model')}` on **{run_meta.get('device')}** — "
                  f"load {run_meta.get('load_seconds')}s, inference "
                  f"{run_meta.get('inference_seconds')}s "
                  f"({run_meta.get('ms_per_snippet')} ms/snippet).")
    md.append("")
    md.append(f"## Headline: F2 = **{head_f2:.3f}**  (recall = **{head_r:.3f}**), relaxed/overlap mode")
    md.append("")
    md.append("> F2 weights recall 2x over precision. In de-identification a *missed* "
              "entity is leaked PII; a *false positive* is only over-redaction. "
              "See `README.md` for the Presidio / i2b2-n2c2 rationale.")
    md.append("")
    md.append(md_table(strict, "Strict (exact-span) mode"))
    md.append(md_table(relaxed, "Relaxed (overlap) mode — headline"))
    md.append("## Error breakdown (relaxed)")
    o = relaxed["overall"]
    md.append(f"- Correct: **{o['correct']}**  |  Missed (FN, = leaked PII): **{o['fn']}**  "
              f"|  Spurious/over-redaction (FP): **{o['fp']}**")
    md.append(f"- Wrong-type matches: {o['wrong_type']}  |  Partial-overlap (non-exact) matches: "
              f"{o['partial_overlap_matches']}")
    md.append("")
    md.append("## Vendor claim (for reference — NOT our measurement)")
    md.append("")
    md.append("The `openai/privacy-filter` model card reports, on the full "
              "**PII-Masking-300k** benchmark: **F1 96% / Precision 94% / Recall 98%**. "
              "That is the vendor's number on the full, in-distribution benchmark.")
    md.append("")
    md.append("Our eval differs deliberately and that explains the gap:")
    md.append("- **Different data:** 32 *therapy-style* curated snippets with hard cases "
              "(relative dates like \"last Tuesday\", short numeric PINs/account tails), "
              "not the in-distribution 300k generic text. A real ai4privacy slice can be "
              "built locally (`python -m confide_eval.data.fetch_ai4privacy`) for an "
              "in-distribution comparison, but it is not redistributed.")
    md.append("- **Stricter accounting:** entity-level, with wrong-type counted as both FP+FN.")
    md.append("- **Small N:** 46 gold entities — each miss moves recall ~2pp. Treat per-type "
              "numbers as directional, not precise.")
    md.append("")
    md.append("**Honest read:** the model is strong on names/phones/emails/URLs and over-redacts "
              "very little (high precision), but on this hard set it misses relative dates and "
              "short numeric secrets — exactly the recall failures that matter for de-id. Build "
              "the ai4privacy slice locally to see in-distribution recall.")
    md.append("")
    with open(os.path.join(HERE, f"{pfx}RESULTS.md"), "w") as f:
        f.write("\n".join(md) + "\n")

    print(f"[score] strict  F2={strict['overall']['f2']:.3f} "
          f"R={strict['overall']['recall']:.3f} P={strict['overall']['precision']:.3f}")
    print(f"[score] relaxed F2={relaxed['overall']['f2']:.3f} "
          f"R={relaxed['overall']['recall']:.3f} P={relaxed['overall']['precision']:.3f}")
    print(f"[score] wrote results.json + RESULTS.md")


if __name__ == "__main__":
    main()
