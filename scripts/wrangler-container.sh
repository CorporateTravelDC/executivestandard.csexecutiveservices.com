#!/usr/bin/env bash
# scripts/wrangler-container.sh -- runs `wrangler` inside the node:20-alpine
# podman image, NOT installed on the host. Mirrors
# csexecutiveservices-website/scripts/wrangler-container.sh (the proven
# pattern) so both sites deploy the same containerized way. See that script's
# header for the full rationale on each hardening choice below.
#
# Executive Standard difference: the built site lives at /var/www (written by
# executive_standard_sync.py), not in this repo, so we mount the DEPLOY dir,
# not the repo. Override with DEPLOY_DIR=... for a scoped dist/.
#
# Usage: scripts/wrangler-container.sh <wrangler args...>
#   deploy : scripts/wrangler-container.sh pages deploy /site \
#              --project-name executivestandard --commit-dirty=true
#   secret : printf '%s' "$TOKEN" | scripts/wrangler-container.sh \
#              pages secret put SECRET_RSS_TOKEN --project-name executivestandard
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SECRETS_ENV="/etc/corporatetraveldc/dispatch-secrets.env"
# Default to the CLEAN assembled dist/ (user-owned, relabelable), NOT /var/www
# -- /var/www is root-owned httpd_sys_content_t and podman's :Z relabel is
# denied there ("operation not permitted"). Run assemble-pages-dist.sh first.
DEPLOY_DIR="${DEPLOY_DIR:-${REPO_DIR}/dist}"

export CLOUDFLARE_API_TOKEN="$(grep -E '^CF_MANAGEMENT_API_TOKEN=' "${SECRETS_ENV}" 2>/dev/null | tail -1 | cut -d'=' -f2-)"
# Account-scoped token can't satisfy wrangler's /memberships discovery
# (user-scoped); setting the account id explicitly skips it. Same fix as csexec.
export CLOUDFLARE_ACCOUNT_ID="$(grep -E '^CF_ACCOUNT_ID=' "${SECRETS_ENV}" 2>/dev/null | tail -1 | cut -d'=' -f2-)"
if [[ -z "${CLOUDFLARE_API_TOKEN}" || -z "${CLOUDFLARE_ACCOUNT_ID}" ]]; then
    echo "XX CF_MANAGEMENT_API_TOKEN or CF_ACCOUNT_ID not set in ${SECRETS_ENV}" >&2
    exit 2
fi
if [[ ! -d "${DEPLOY_DIR}" ]]; then
    echo "XX DEPLOY_DIR ${DEPLOY_DIR} does not exist" >&2
    exit 2
fi

# Shared npx cache volume (skip re-fetching wrangler each run); never touches
# the host fs outside podman's volume store.
podman volume create --ignore executivestandard-wrangler-npm-cache >/dev/null

echo "[wrangler-container] deploy dir: ${DEPLOY_DIR}"
echo "[wrangler-container] running: wrangler $*"
# Deploy dir mounted at /site READ-ONLY -- a deploy tool never needs to write
# the artifact it uploads, and ro means a compromised wrangler can't alter what
# gets served. Single -e per secret so nothing else in dispatch-secrets.env
# reaches this throwaway container. 30-min timeout is a hang net, not a budget
# (this Pi downloads native arm64 blobs slowly; killing mid-install corrupts the
# npx cache -- see csexec script header).
timeout 1800 podman run --rm \
    -e CLOUDFLARE_API_TOKEN \
    -e CLOUDFLARE_ACCOUNT_ID \
    -e CI=true \
    -e WRANGLER_SEND_METRICS=false \
    -v "${DEPLOY_DIR}:/site:ro,Z" \
    -v "executivestandard-wrangler-npm-cache:/root/.npm:Z" \
    -w /site \
    docker.io/library/node:20-alpine \
    npx --yes wrangler@4 "$@"
