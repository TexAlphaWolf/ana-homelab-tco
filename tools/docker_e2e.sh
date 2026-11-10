#!/usr/bin/env bash
# End to end inside the image (read-only root, no capabilities, no network): the example scenario is written to a
# volume, validated, analysed, checked against the literal simulation, benchmarked, and the result files are checked.
# Needs Docker. Usage: tools/docker_e2e.sh [image]
set -euo pipefail
IMAGE="${1:-tco}"
VOL="tco-e2e-$$"
TMP="$(mktemp -d)"
trap 'docker volume rm -f "$VOL" >/dev/null 2>&1 || true; rm -rf "$TMP"' EXIT

[ "$(docker run --rm --entrypoint id "$IMAGE" -u)" != 0 ]   # not root
docker volume create "$VOL" >/dev/null
docker run --rm --user 0 -v "$VOL":/data --entrypoint chown "$IMAGE" 10001 /data

RUN=(docker run --rm --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges --network none -v "$VOL":/data "$IMAGE")
cat_file() { docker run --rm --entrypoint cat -v "$VOL":/data "$IMAGE" "$1" > "$2"; }

out="$("${RUN[@]}" example -o /data/home.yaml)"
grep -q 'written: /data/home.yaml' <<<"$out"
out="$("${RUN[@]}" validate /data/home.yaml)"
grep -q '^ok: Home server, four-bay build; 5 hardware items (€2,230), 3 cloud alternatives, 60 months' <<<"$out"

out="$("${RUN[@]}" run /data/home.yaml --samples 2000 --out /data/out)"
grep -q '^home server: cash €4,258, residual value €236, net €4,021 (€67 a month)' <<<"$out"
grep -q 'break-even month 21 (2027-09)' <<<"$out"
cat_file /data/out/report.json "$TMP/report.json"
grep -q '"kind": "report"' "$TMP/report.json"
cat_file /data/out/report.md "$TMP/report.md"
"${RUN[@]}" render /data/out/report.json -o /data/out/again.md >/dev/null
cat_file /data/out/again.md "$TMP/again.md"
cmp "$TMP/again.md" "$TMP/report.md"                              # the report is rebuilt exactly from the JSON
cat_file /data/out/summary.png "$TMP/summary.png"
[ "$(head -c 4 "$TMP/summary.png" | tail -c 3)" = "PNG" ]

out="$("${RUN[@]}" verify /data/home.yaml --draws 5)"
grep -q '^6 of 6 comparisons agree with the literal simulation' <<<"$out"

"${RUN[@]}" bench /data/home.yaml --sizes 500,1000 --repeat 1 --draws 3 --out /data/bench >/dev/null
cat_file /data/bench/bench.json "$TMP/bench.json"
grep -q '"ok": true' "$TMP/bench.json"

set +e; "${RUN[@]}" validate /data/nope.yaml >/dev/null 2>&1; rc=$?; set -e   # a missing file is exit code 2
[ "$rc" = 2 ]
echo "docker end-to-end: OK"
