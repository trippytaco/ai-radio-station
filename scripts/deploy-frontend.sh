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

echo "==> Syncing checkout at $REPO_DIR"
mkdir -p "$REPO_DIR"
if [ -d "$REPO_DIR/.git" ]; then
    "$DOCKER_BIN" run --rm -v "$REPO_DIR:/repo" -w /repo alpine/git:latest \
        pull --ff-only
else
    "$DOCKER_BIN" run --rm -v "$REPO_DIR:/repo" alpine/git:latest \
        clone --depth 1 "$REPO_URL" /repo
fi

echo "==> Building frontend image"
cd "$REPO_DIR"
"$DOCKER_BIN" compose -f docker-compose.frontend.yml build

echo "==> Recreating ai-radio-frontend"
"$DOCKER_BIN" compose -f docker-compose.frontend.yml up -d --force-recreate

echo "==> Done. Serving on port 8080."
