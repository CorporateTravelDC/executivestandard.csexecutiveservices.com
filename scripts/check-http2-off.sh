#!/usr/bin/env bash
# check-http2-off.sh -- 2026-11-19 (operator: HTTP/2 disabled everywhere, nginx HTTP/2 CVE; re-enable only on nginx >= 1.31.9).
# Exits 1 if any nginx config in this repo has an active `http2 on` or a legacy `listen ... http2`.
cd "$(dirname "$0")/.." || exit 2
if grep -rnE '^[[:space:]]*http2[[:space:]]+on[[:space:]]*;|^[[:space:]]*listen[^;#]*[[:space:]]http2' nginx/; then
  echo "check-http2-off: HTTP/2 enabled above -- must stay off until nginx >= 1.31.9" >&2; exit 1
fi
echo "check-http2-off: OK (no active http2 in nginx/)"
