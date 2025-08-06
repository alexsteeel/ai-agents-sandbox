#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures

# Build Docker image for Claude Code Sandbox
# This script builds the development container image

readonly IMAGE_NAME="claude-code-sandbox"
readonly IMAGE_TAG="1.0"

# Check if Dockerfile exists
if [[ ! -f "Dockerfile" ]]; then
    echo "Error: Dockerfile not found in current directory"
    exit 1
fi

echo "Building Docker image: ${IMAGE_NAME}:${IMAGE_TAG}"

# Build the image
docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .

echo ""
echo "Build completed successfully!"
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"