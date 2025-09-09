# AI Agents Sandbox - Minimal Image
# Ultra-lightweight image with only essential tools

FROM debian:bookworm-slim

# Build arguments
ARG USERNAME=claude
ARG USER_UID=1001
ARG USER_GID=1001
ARG WORKSPACE_GID=3000
ARG WORKSPACE_GROUPNAME=local-ai-team

# Install absolute minimum packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create groups and user
RUN groupadd --gid "$USER_GID" "$USERNAME" \
    && groupadd --gid "$WORKSPACE_GID" "$WORKSPACE_GROUPNAME" \
    && useradd --uid "$USER_UID" --gid "$USER_GID" -m "$USERNAME" \
    && usermod -aG "$WORKSPACE_GROUPNAME" "$USERNAME"

# Set up workspace
RUN mkdir -p /workspace \
    && chown -R $USERNAME:$USERNAME /workspace

# Set environment
ENV DEVCONTAINER=true

# Switch to non-root user
USER $USERNAME
WORKDIR /workspace

CMD ["sleep", "infinity"]