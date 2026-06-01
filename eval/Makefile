# CONFIDE-Bench — regeneration + drift-check targets.
# `make check` is the deterministic stale-guard (no LLM calls); see REPRODUCIBILITY.md §8.
PY ?= python3
DATASETS := ru ru-adv en en-real

.PHONY: check rescore ci report all

## check: fail if any committed artifact drifted from current gold + caches
check:
	$(PY) check_artifacts.py

## rescore: re-score every dataset + bootstrap CIs from the current caches
rescore:
	@for d in $(DATASETS); do \
	  pfx=$$d-; \
	  echo "== score $$d =="; $(PY) score_bench.py --dataset $$d --out-prefix $$pfx; \
	  echo "== ci $$d =="; $(PY) bootstrap_ci.py --dataset $$d; \
	done
	$(PY) score_bench.py --dataset ru   # refresh the legacy unprefixed bench-results.json

## ci: refresh the IAA consistency check (single LLM second-annotator)
ci:
	$(PY) iaa_eval.py

## report: regenerate BENCHMARK.md + the HTML report from the JSONs
report:
	$(PY) make_benchmark.py
	$(PY) make_tufte_report.py

## all: full regeneration, then verify nothing is stale
all: rescore ci report check
