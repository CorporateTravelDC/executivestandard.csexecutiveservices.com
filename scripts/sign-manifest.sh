#!/usr/bin/env bash
# scripts/sign-manifest.sh
# Generates and GPG-signs a whole-repo-tree integrity manifest for this repo
# -- same mechanism as csexecutiveservices-website's identical script.
#
# This is a DELIBERATE, human-run step: nothing re-signs the manifest
# automatically. Run this after making changes you're ready to trust, as
# part of the same review/commit pass, using your own GPG passphrase.
#
# Usage:
#   scripts/sign-manifest.sh
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_DIR}"

ENV_FILE="security/signing.env"
if [[ ! -f "${ENV_FILE}" ]]; then
    echo "XX Missing ${ENV_FILE} -- copy security/signing.env.example, fill in your" >&2
    echo "   own SIGNING_KEY_FINGERPRINT, and re-run." >&2
    exit 2
fi
# shellcheck source=/dev/null
source "${ENV_FILE}"
: "${SIGNING_KEY_FINGERPRINT:?SIGNING_KEY_FINGERPRINT not set in ${ENV_FILE}}"
if [[ "${SIGNING_KEY_FINGERPRINT}" == "0000000000000000000000000000000000000000" ]]; then
    echo "XX ${ENV_FILE} still has the placeholder fingerprint -- fill in your real one." >&2
    exit 2
fi

MANIFEST="MANIFEST.sha256"
SIGNATURE="MANIFEST.sha256.asc"

TMP_MANIFEST="$(mktemp "${MANIFEST}.XXXXXX")"
trap 'rm -f "${TMP_MANIFEST}" "${TMP_SIGNATURE:-}"' EXIT

echo "[sign-manifest] Hashing every tracked AND untracked-but-not-ignored file (true whole-repo-tree coverage)..."
git ls-files --cached --others --exclude-standard -z \
    | grep -zvE "^(${MANIFEST}(\..*)?|contact-api/${MANIFEST}(\..*)?)\$" \
    | xargs -0 sha256sum \
    | sort -k2 \
    > "${TMP_MANIFEST}"

echo "[sign-manifest] $(wc -l < "${TMP_MANIFEST}") files covered."
echo "[sign-manifest] Signing with key ${SIGNING_KEY_FINGERPRINT} (you'll be prompted for your passphrase)..."
TMP_SIGNATURE="$(mktemp "${SIGNATURE}.XXXXXX")"
if gpg --local-user "${SIGNING_KEY_FINGERPRINT}" --detach-sign --armor --yes \
        -o "${TMP_SIGNATURE}" "${TMP_MANIFEST}"; then
    mv "${TMP_MANIFEST}" "${MANIFEST}"
    mv "${TMP_SIGNATURE}" "${SIGNATURE}"
else
    echo "[sign-manifest] FAILED -- gpg did not produce a signature (see error above)." >&2
    echo "[sign-manifest] ${MANIFEST} + ${SIGNATURE} left untouched -- no valid pair was destroyed." >&2
    exit 1
fi

echo "[sign-manifest] OK -- ${MANIFEST} + ${SIGNATURE} written."

# contact-api's image has always been built with contact-api/ itself as the
# build context, so it can't COPY from ../security or ../MANIFEST.sha256
# directly. Keep its duplicated copies in lockstep by refreshing them on
# every sign, rather than relying on someone remembering to do it by hand.
# No-op until contact-api/ actually exists in this repo.
if [[ -d "contact-api" ]]; then
    cp "${MANIFEST}" "${SIGNATURE}" "security/trusted-signing-key.pub.asc" contact-api/
    echo "[sign-manifest] Refreshed contact-api/'s duplicated manifest + pubkey copies."
fi

echo "[sign-manifest] Verify with: scripts/verify-manifest.sh"
echo "[sign-manifest] Remember to commit both files (and contact-api/'s refreshed copies, if present) alongside the changes they cover."
