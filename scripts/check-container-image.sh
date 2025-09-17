#!/bin/bash
#
# Container Image Fallback Script
#
# This script provides image fallback logic for container deployments.
# Since we can't easily check image existence without authentication,
# we'll implement a configurable fallback strategy.
#
# Usage:
#   ./scripts/check-container-image.sh <container_name> <requested_tag> [fallback_strategy]
#
# Fallback strategies:
#   latest    - Fall back to :latest tag (default)
#   main      - Fall back to :main tag
#   none      - No fallback, use requested tag as-is
#
# Returns JSON:
#   {"image_url": "ghcr.io/hardcoreprawn/ai-content-farm/container:tag", "fallback_used": "false|true"}

set -euo pipefail

if [[ $# -lt 2 ]] || [[ $# -gt 3 ]]; then
    echo "Usage: $0 <container_name> <requested_tag> [fallback_strategy]" >&2
    exit 1
fi

CONTAINER_NAME="$1"
REQUESTED_TAG="$2"
FALLBACK_STRATEGY="${3:-latest}"
REGISTRY="ghcr.io/hardcoreprawn/ai-content-farm"
IMAGE_BASE="${REGISTRY}/${CONTAINER_NAME}"

# Determine if we should use fallback based on tag patterns
use_fallback=false

# If the requested tag looks like a commit hash (long alphanumeric string)
# and we're configured to use fallback, then use the fallback strategy
if [[ ${#REQUESTED_TAG} -ge 32 ]] && [[ "$REQUESTED_TAG" =~ ^[a-f0-9]+$ ]] && [[ "$FALLBACK_STRATEGY" != "none" ]]; then
    use_fallback=true
    echo "[INFO] Detected commit hash tag '$REQUESTED_TAG', using fallback strategy '$FALLBACK_STRATEGY'" >&2
fi

if [[ "$use_fallback" == "true" ]]; then
    FINAL_IMAGE="${IMAGE_BASE}:${FALLBACK_STRATEGY}"
    echo "[INFO] Using fallback image: $FINAL_IMAGE" >&2
    echo "{\"image_url\": \"$FINAL_IMAGE\", \"fallback_used\": \"true\"}"
else
    FINAL_IMAGE="${IMAGE_BASE}:${REQUESTED_TAG}"
    echo "[INFO] Using requested image: $FINAL_IMAGE" >&2
    echo "{\"image_url\": \"$FINAL_IMAGE\", \"fallback_used\": \"false\"}"
fi
