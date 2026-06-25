#!/usr/bin/env bash
# Standard update pipeline for benchmark defaults/results changes:
#   1. regenerate regulatory metrics, BENCHMARK.md and the EN/RU HTML reports
#   2. sync generated data into the Astro site (site/src/data/model-swaps.json)
#   3. build the site locally and deploy the prebuilt output to Vercel prod
#      (cloud builds fail on ../docs imports outside site/, hence --prebuilt)
#   4. verify the deployed pages render the synced numbers
#
# Usage:  tools/update_site.sh [--no-deploy]
set -euo pipefail
cd "$(dirname "$0")/.."

NO_DEPLOY=0
[ "${1:-}" = "--no-deploy" ] && NO_DEPLOY=1

echo "==> 1/4 regenerating reports"
make report

echo "==> 2/4 syncing site data"
make site-data

if [ "$NO_DEPLOY" = 1 ]; then
  echo "==> --no-deploy: building only"
  (cd site && npm run build)
  echo "done (no deploy)."
  exit 0
fi

echo "==> 3/4 building + deploying site"
make site-deploy

echo "==> 4/4 verifying deployed pages"
SITE_URL="${SITE_URL:-https://confide.salient.community}"
fail=0
for path in /benchmark/ /report/benchmark-report.html /report/benchmark-report.ru.html; do
  body=$(curl -sf "$SITE_URL$path") || { echo "FAIL: $path unreachable"; fail=1; continue; }
  if printf '%s' "$body" | grep -qi "billing"; then
    echo "FAIL: $path mentions billing"; fail=1
  fi
done
# the site table and the report must show the same first model-swap value
first_val=$(python3 -c "import json;d=json.load(open('site/src/data/model-swaps.json'));print(d[0][1][0][1])")
if curl -sf "$SITE_URL/benchmark/" | grep -q "$first_val"; then
  echo "OK: site table carries synced value $first_val"
else
  echo "FAIL: deployed /benchmark/ missing synced value $first_val"; fail=1
fi
[ "$fail" = 0 ] && echo "site update verified." || { echo "site update FAILED verification"; exit 1; }
