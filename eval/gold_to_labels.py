#!/usr/bin/env python3
"""Convert an existing gold JSONL into annotator-tool label files — so you can TEST the
IAA pipeline without recruiting two people yet: treat the gold as one "annotator" and
your own labels (from annotator.html) as another, then run score_iaa.py.

Emits one `labels.<doc_id>.<name>.json` per doc, in the exact schema annotator.html
exports, into --out-dir. Reads the transcript text from the session files so the
char-offset length matches.

Usage:
  python3 gold_to_labels.py --gold ../sessions-ru/pii-eval-ru.jsonl --name gold --out-dir labels/
  # then label a session yourself in annotator.html (id e.g. "me"), drop labels.*.me.json
  # into labels/, and: python3 score_iaa.py --labels-dir labels/
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))


def doc_to_path(doc_id):
    """ru-a-s01 -> ../sessions-ru/client-a/session-01.md"""
    m = re.match(r"ru-([a-z])-s(\d+)", doc_id)
    if m:
        return os.path.join(HERE, "..", "sessions-ru", f"client-{m.group(1)}", f"session-{int(m.group(2)):02d}.md")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=os.path.join(HERE, "..", "sessions-ru", "pii-eval-ru.jsonl"))
    ap.add_argument("--name", default="gold", help="annotator name to stamp")
    ap.add_argument("--out-dir", default=os.path.join(HERE, "labels"))
    ap.add_argument("--only", help="comma-separated doc_ids to emit (default: all)")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)
    only = set(args.only.split(",")) if args.only else None

    rows = [json.loads(l) for l in open(args.gold, encoding="utf-8")]
    n = 0
    for i, r in enumerate(rows):
        doc_id = r.get("doc_id", f"doc-{i:03d}")
        if only and doc_id not in only:
            continue
        path = doc_to_path(doc_id)
        text = open(path, encoding="utf-8").read() if path and os.path.exists(path) else r.get("text", "")
        spans = [{
            "start": s["start"], "end": s["end"], "text": s.get("value", text[s["start"]:s["end"]]),
            "type": s["type"], "identifier_class": s.get("identifier_class", "direct"),
            "entity_id": s.get("entity_id", ""), "person_role": s.get("person_role", "client"),
            "harm": s.get("harm", "medium"), "note": "",
        } for s in r["spans"]]
        out = {"doc_id": doc_id, "annotator": args.name, "codebook": "gold-derived", "text": text, "spans": spans}
        json.dump(out, open(os.path.join(args.out_dir, f"labels.{doc_id}.{args.name}.json"), "w"),
                  ensure_ascii=False, indent=2)
        n += 1
    print(f"[gold->labels] wrote {n} files to {args.out_dir} (annotator='{args.name}')")


if __name__ == "__main__":
    main()
