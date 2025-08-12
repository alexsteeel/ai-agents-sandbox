#!/bin/bash

# Simple notification hook for Claude Code
# Writes notification to a shared file that host can watch

NOTIFY_DIR="/home/claude/.claude/notifications"
PROJECT_NAME="${PROJECT_NAME:-$(basename $(pwd))}"
TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Ensure notification directory exists
mkdir -p "$NOTIFY_DIR" 2>/dev/null || true

# Detect notification type from arguments or context
TYPE="${1:-attention}"
MESSAGE="${2:-Claude needs your attention}"

# Write notification to file (host will watch this)
cat > "$NOTIFY_DIR/notify.txt" << EOF
[$TIMESTAMP] $PROJECT_NAME
Type: $TYPE
Message: $MESSAGE
EOF

# Also append to log
echo "[$TIMESTAMP] $PROJECT_NAME - $TYPE: $MESSAGE" >> "$NOTIFY_DIR/log.txt"

exit 0