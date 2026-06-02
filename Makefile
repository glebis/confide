# CONFIDE-Bench — regeneration + drift-check targets.
# `make check` is the deterministic stale-guard (no LLM calls); see docs/REPRODUCIBILITY.md §8.
# The eval suite is an installable package (src/confide_eval); modules are run
# via `python -m confide_eval.<subpkg>.<module>`. PYTHONPATH=src lets it run
# without an editable install.
PY ?= PYTHONPATH=src python3
DATASETS := ru ru-adv en en-real ru-real

.PHONY: check test rescore ci report all

## check: fail if any committed artifact drifted from current gold + caches
check:
	$(PY) -m confide_eval.registry.check_artifacts

## test: run the deterministic unit test suite
test:
	$(PY) -m pytest tests/

## rescore: re-score every dataset + bootstrap CIs from the current caches
rescore:
	@for d in $(DATASETS); do \
	  pfx=$$d-; \
	  echo "== score $$d =="; $(PY) -m confide_eval.scoring.score_bench --dataset $$d --out-prefix $$pfx; \
	  echo "== ci $$d =="; $(PY) -m confide_eval.scoring.bootstrap_ci --dataset $$d; \
	done
	$(PY) -m confide_eval.scoring.score_bench --dataset ru   # refresh the legacy unprefixed bench-results.json

## ci: refresh the IAA consistency check (single LLM second-annotator)
ci:
	$(PY) -m confide_eval.annotation.iaa_eval

## report: regenerate regulatory metrics + BENCHMARK.md + the HTML report from the JSONs
report:
	$(PY) -m confide_eval.scoring.regulatory
	$(PY) -m confide_eval.report.make_benchmark
	$(PY) -m confide_eval.report.make_tufte_report

## all: full regeneration, then verify nothing is stale
all: rescore ci report check
