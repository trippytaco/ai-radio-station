#!/bin/bash
# Deploys/updates the RadioMe frontend on a host with no git binary at the
# OS level (confirmed live on the QNAP: neither the host nor its Docker
# BuildKit git-context support has one) but with a working `docker` CLI.
#
# What it does:
#   1. Clones/pulls this repo into a stable local checkout, using an
#      alpine/git container (the same pattern the QNAP's other homelab
#      stacks already use for this exact problem) rather than needing git
#      installed anywhere.
#   2. Builds the frontend image from that LOCAL checkout (a local build
#      context needs no git at all, unlike a git-URL context).
#   3. Recreates the ai-radio-frontend container.
#
# Usage (run on the Docker host, e.g. via SSH to the QNAP):
#   ./scripts/deploy-frontend.sh
#
# Override the checkout location or Docker binary path if needed:
#   REPO_DIR=/some/path DOCKER_BIN=/some/docker ./scripts/deploy-frontend.sh

set -euo pipefail

REPO_URL="https://github.com/trippytaco/ai-radio-station.git"
REPO_DIR="${REPO_DIR:-$HOME/ai-radio-station-repo}"
DOCKER_BIN="${DOCKER_BIN:-docker}"

# On this QNAP, Container Station's docker binary resolves BuildKit's
# state dir under its own install path regardless of the shell's $HOME
# (confirmed live: it tried /share/CACHEDEV1_DATA/.qpkg/container-station/
# homes/<user>, which this user can't write to), causing `docker compose
# build` to fail with a permission error. Pointing HOME/DOCKER_CONFIG at
# somewhere actually writable works around it. Harmless no-op on a normal
# Docker host where $HOME is already writable.
export HOME="${HOME:-/tmp}"
export DOCKER_CONFIG="${DOCKER_CONFIG:-$HOME/.docker-buildx}"

echo "==> Syncing checkout at $REPO_DIR"
mkdir -p "$REPO_DIR"
# Run as the current UID/GID, not the image's default root - otherwise
# every file it writes into the bind mount is root-owned and this script
# (running as a normal user) can't clean up or re-pull next time.
if [ -d "$REPO_DIR/.git" ]; then
    "$DOCKER_BIN" run --rm --user "$(id -u):$(id -g)" -v "$REPO_DIR:/repo" -w /repo alpine/git:latest \
        pull --ff-only
else
    "$DOCKER_BIN" run --rm --user "$(id -u):$(id -g)" -v "$REPO_DIR:/repo" alpine/git:latest \
        clone --depth 1 "$REPO_URL" /repo
fi

echo "==> Building frontend image"
cd "$REPO_DIR"
"$DOCKER_BIN" compose -f docker-compose.frontend.yml build

echo "==> Recreating ai-radio-frontend"
"$DOCKER_BIN" compose -f docker-compose.frontend.yml up -d --force-recreate

echo "==> Done. Serving on port 8090."
