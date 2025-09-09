# AI Agents Sandbox - Node.js Development Image
# Extends the base image with Node.js development tools

FROM ai-agents-sandbox/base:latest

# Already has Node.js 20 from base image
# Add additional Node.js development tools

USER root

# Install additional development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install global npm packages for development
RUN npm install -g \
    typescript \
    ts-node \
    nodemon \
    eslint \
    prettier \
    jest \
    npm-check-updates \
    yarn \
    pnpm

# Switch back to non-root user
USER claude

# Configure npm for user installations
RUN mkdir -p /home/claude/.npm-global \
    && npm config set prefix '/home/claude/.npm-global'

ENV PATH="/home/claude/.npm-global/bin:${PATH}"
ENV NODE_ENV=development

WORKDIR /workspace

# Initialization script for Node.js projects
COPY --chown=claude:local-ai-team <<'EOF' /home/claude/init-nodejs.sh
#!/bin/bash
set -euo pipefail

echo "Initializing Node.js environment..."

# Install project dependencies if they exist
if [ -f "package.json" ]; then
    if [ -f "yarn.lock" ]; then
        echo "Installing dependencies with Yarn..."
        yarn install
    elif [ -f "pnpm-lock.yaml" ]; then
        echo "Installing dependencies with pnpm..."
        pnpm install
    else
        echo "Installing dependencies with npm..."
        npm install
    fi
fi

echo "Node.js environment ready!"
EOF

RUN chmod +x /home/claude/init-nodejs.sh

CMD ["sleep", "infinity"]