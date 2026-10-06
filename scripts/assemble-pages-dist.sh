#!/usr/bin/env bash
# scripts/assemble-pages-dist.sh -- build a CLEAN Cloudflare Pages deploy dir.
#
# Why this exists (2026-09-26): deploying /var/www directly is wrong on two axes.
#   1. SELinux: /var/www is root-owned httpd_sys_content_t; podman's :Z relabel
#      fails ("operation not permitted") and would break nginx if it didn't.
#   2. Hygiene: /var/www holds the nginx doc root PLUS build/source/signing
#      material (_md/ source, security/, MANIFEST.*). A wholesale Pages upload
#      would publish those. The gate blocks SERVING them; this stops UPLOADING
#      them at all -- the stronger rule.
#
# So we assemble dist/ in the repo (user-owned, relabelable) with ONLY what
# should be public: the built site + functions/ + gate/ + the tokenised feed.
#
# Usage: sudo scripts/assemble-pages-dist.sh   (sudo: reads root-owned /var/www)
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SITE_DIR="${SITE_DIR:-/var/www/executivestandard.csexecutiveservices.com}"
DIST="${DIST:-${REPO_DIR}/dist}"
OWNER="$(stat -c '%U' "${REPO_DIR}")"

[[ -d "${SITE_DIR}" ]] || { echo "XX ${SITE_DIR} missing" >&2; exit 2; }

rm -rf "${DIST}"; mkdir -p "${DIST}"

# 1. Built site from /var/www, EXCLUDING everything non-public. The feed
#    (feed<token>.xml) is NOT excluded -- it is meant to be served (gated by the
#    token path). functions/ from /var/www is excluded; the canonical copy comes
#    from the repo in step 2.
rsync -a \
  --exclude 'security/' \
  --exclude '_md/' \
  --exclude 'functions/' \
  --exclude 'MANIFEST.sha256' \
  --exclude 'MANIFEST.sha256.asc' \
  --exclude 'config.json' \
  --exclude '.git/' \
  "${SITE_DIR}/" "${DIST}/"

# 2. Canonical gate assets + Pages Functions from the REPO (reviewed/signed
#    source, not the /var/www copies).
cp -r "${REPO_DIR}/functions" "${DIST}/functions"
cp -r "${REPO_DIR}/gate"      "${DIST}/gate"

# 3. Belt-and-suspenders: assert nothing sensitive slipped in.
for bad in security _md config.json MANIFEST.sha256 MANIFEST.sha256.asc; do
  if [[ -e "${DIST}/${bad}" ]]; then
    echo "XX ${bad} present in dist -- refusing. Fix the exclude list." >&2
    exit 3
  fi
done

# 4. Hand ownership back so the containerized wrangler (rootless) can relabel it.
chown -R "${OWNER}:${OWNER}" "${DIST}"

FEED_COUNT="$(ls "${DIST}"/feed*.xml 2>/dev/null | wc -l)"
echo "OK  dist assembled at ${DIST}"
echo "    $(find "${DIST}" -type f | wc -l) files; ${FEED_COUNT} feed file(s); no security/_md/MANIFEST/config"
echo "    deploy with: DEPLOY_DIR='${DIST}' scripts/wrangler-container.sh pages deploy /site --project-name executivestandard --commit-dirty=true"
