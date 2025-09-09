# AI Agents Sandbox - Minimal Base Image
# This is the foundation image with essential tools only
# No Claude-specific settings or configurations

FROM node:20-bookworm-slim

# Build arguments
ARG USERNAME=claude
ARG USER_UID=1001
ARG USER_GID=1001
ARG WORKSPACE_GID=3000
ARG WORKSPACE_GROUPNAME=local-ai-team

# Install essential system packages only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    git \
    ca-certificates \
    gnupg2 \
    lsb-release \
    sudo \
    procps \
    iproute2 \
    dnsutils \
    iputils-ping \
    jq \
    vim \
    less \
    locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Generate locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Install Docker CLI for Docker-in-Docker support
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update \
    && apt-get install -y docker-ce-cli \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create groups and user
RUN groupadd --gid "$USER_GID" "$USERNAME" \
    && groupadd --gid "$WORKSPACE_GID" "$WORKSPACE_GROUPNAME" \
    && useradd --uid "$USER_UID" --gid "$USER_GID" -m "$USERNAME" \
    && usermod -aG "$WORKSPACE_GROUPNAME" "$USERNAME" \
    && usermod -aG docker "$USERNAME" 2>/dev/null || true

# Set up directories with proper permissions
RUN mkdir -p /workspace /home/$USERNAME/.cache \
    && chown -R $USERNAME:$USERNAME /workspace /home/$USERNAME

# Set environment variables
ENV DEVCONTAINER=true
ENV SHELL=/bin/bash
ENV UMASK=0002

# Switch to non-root user
USER $USERNAME
WORKDIR /workspace

# Basic entrypoint that just sleeps
CMD ["sleep", "infinity"]