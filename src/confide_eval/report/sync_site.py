#!/usr/bin/env python3
"""Sync generated benchmark data into the Astro site.

Writes site/src/data/model-swaps.json from the SAME row source the HTML
report uses (make_tufte_report.local_llm_compare_rows), so the site's
"Exploratory model swaps" table can never drift from the report again.
Also copies docs/CHANGELOG.md into site/src/data/ so the /changelog page
renders the canonical changelog without importing across the site root
(../docs imports break Vercel cloud builds).

The ★ default is marked on the Qwen2.5-3B rows; numbers are pre-formatted
strings so the Astro template stays a dumb renderer.

Run via:  PYTHONPATH=src python3 -m confide_eval.report.sync_site
(or `make site-data`; `tools/update_site.sh` chains report → data → deploy.)
"""
import json
import os
import shutil

from confide_eval import paths
from confide_eval.report.make_tufte_report import local_llm_compare_rows

SITE_DATA = os.path.join(os.fspath(paths.ROOT), "site", "src", "data")
CHANGELOG = os.path.join(os.fspath(paths.DOCS), "CHANGELOG.md")


def model_swaps_payload():
    groups: dict[str, list] = {}
    order: list[str] = []
    for r in local_llm_compare_rows():
        label = r["dataset_label"]
        if label not in groups:
            groups[label] = []
            order.append(label)
        model = r["model"]
        if model == "Qwen2.5-3B":
            model += " ★"
        groups[label].append([
            model,
            f"{r['cov_r']:.3f}",
            f"{r['type_f2']:.3f}",
            f"{r['ent_r']:.3f}" if r["ent_r"] is not None else "—",
        ])
    return [[label, groups[label]] for label in order]


def main():
    os.makedirs(SITE_DATA, exist_ok=True)
    out = os.path.join(SITE_DATA, "model-swaps.json")
    payload = model_swaps_payload()
    tmp = f"{out}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, out)
    n_rows = sum(len(rows) for _, rows in payload)
    print(f"[sync-site] wrote {os.path.relpath(out, os.fspath(paths.ROOT))} "
          f"({len(payload)} datasets, {n_rows} rows)")

    if os.path.exists(CHANGELOG):
        dst = os.path.join(SITE_DATA, "CHANGELOG.md")
        shutil.copyfile(CHANGELOG, dst)
        print(f"[sync-site] copied docs/CHANGELOG.md -> "
              f"{os.path.relpath(dst, os.fspath(paths.ROOT))}")


if __name__ == "__main__":
    main()
