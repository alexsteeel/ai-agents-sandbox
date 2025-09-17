#!/bin/bash

# Simple notification hook for Claude Code
# Writes notification to a shared file that host can watch

NOTIFY_DIR="/home/claude/.ai-sbx/notifications"
PROJECT_NAME="${PROJECT_NAME:-$(basename $(pwd))}"
TIMESTAMP=$(date +"%Y-%m-%d_%H%M%S")

# Ensure notification directory exists
mkdir -p "$NOTIFY_DIR" 2>/dev/null || true

# Detect notification type from arguments or context
TYPE="${1:-attention}"
MESSAGE="${2:-Claude needs your attention}"

# Generate unique filename to avoid race conditions
FILENAME="notify_${TIMESTAMP}_$$.txt"

# Write notification in format expected by Python: type|title|message
echo "${TYPE}|${PROJECT_NAME}|${MESSAGE}" > "$NOTIFY_DIR/$FILENAME"

# Also append to log for debugging
echo "[$TIMESTAMP] $PROJECT_NAME - $TYPE: $MESSAGE" >> "$NOTIFY_DIR/log.txt"

exit 0