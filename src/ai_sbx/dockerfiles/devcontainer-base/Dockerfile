FROM node:20

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest

# Install basic development tools and linters
RUN apt-get update && apt-get install -y --no-install-recommends \
  less \
  git \
  procps \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  iproute2 \
  dnsutils \
  iputils-ping \
  aggregate \
  jq \
  vim \
  tmux \
  fonts-powerline \
  locales \
  wget \
  ca-certificates \
  shellcheck \
  yamllint \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Docker CLI
ARG DOCKER_CLI_VERSION="5:28.0.0-1~debian.12~bookworm"
RUN apt-get update && apt-get install -y lsb-release \
  && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
  && apt-get update \
  && apt-get install -y docker-ce-cli=${DOCKER_CLI_VERSION} \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ARG USERNAME=claude
ARG USER_UID=1001
ARG USER_GID=1001
ARG WORKSPACE_GID=3000
ARG WORKSPACE_GROUPNAME=local-ai-team

RUN set -eux; \
    getent group "$USER_GID" || groupadd --gid "$USER_GID" "$USERNAME"; \
    getent group "$WORKSPACE_GID" || groupadd --gid "$WORKSPACE_GID" "$WORKSPACE_GROUPNAME"; \
    id -u "$USERNAME" >/dev/null 2>&1 || useradd --uid "$USER_UID" --gid "$USER_GID" -m "$USERNAME"; \
    # add to local-ai-team regardless
    usermod -aG "$WORKSPACE_GROUPNAME" "$USERNAME"; \
    # add to docker only if it exists
    if getent group docker >/dev/null; then usermod -aG docker "$USERNAME"; fi


# Generate locale
RUN locale-gen en_US.UTF-8

RUN mkdir -p /usr/local/share/npm-global && \
  chown -R $USERNAME:$USERNAME /usr/local/share

# Persist bash history.
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
  && mkdir /commandhistory \
  && touch /commandhistory/.bash_history \
  && chown -R $USERNAME /commandhistory

# Set `DEVCONTAINER` environment variable to help with orientation
ENV DEVCONTAINER=true

# Create workspace and config directories and set permissions
# Pre-create config.json to prevent it being created as root later
RUN mkdir -p /workspace /home/$USERNAME/.ai-sbx /home/$USERNAME/.codex /home/$USERNAME/.cache /home/$USERNAME/.docker && \
  echo '{}' > /home/$USERNAME/.docker/config.json && \
  chown -R $USERNAME:$USERNAME /workspace /home/$USERNAME/.ai-sbx /home/$USERNAME/.codex /home/$USERNAME/.cache /home/$USERNAME/.docker

WORKDIR /workspace

ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

USER root

# Set zsh as the default shell
RUN chsh -s /usr/bin/zsh $USERNAME

# Install hadolint
ENV HADOLINT_VERSION=2.12.0
RUN set -eux; \
    ARCH=$(dpkg --print-architecture); \
    if [ "$ARCH" = "amd64" ]; then HAD_ARCH="x86_64"; \
    elif [ "$ARCH" = "arm64" ]; then HAD_ARCH="arm64"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi; \
    wget -O /usr/local/bin/hadolint \
      "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-${HAD_ARCH}"; \
    chmod +x /usr/local/bin/hadolint

# Install uv (Astral) for running Python hooks and tools
ENV UV_INSTALL_DIR=/usr/local/bin
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Python linting and formatting tools globally using uv
RUN uv pip install --system --break-system-packages --no-cache ruff black

# Install shfmt
ENV SHFMT_VERSION=3.7.0
RUN set -eux; \
    ARCH=$(dpkg --print-architecture); \
    if [ "$ARCH" = "amd64" ]; then SHFMT_ARCH="amd64"; \
    elif [ "$ARCH" = "arm64" ]; then SHFMT_ARCH="arm64"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi; \
    wget -O /usr/local/bin/shfmt \
      "https://github.com/mvdan/sh/releases/download/v${SHFMT_VERSION}/shfmt_v${SHFMT_VERSION}_linux_${SHFMT_ARCH}"; \
    chmod +x /usr/local/bin/shfmt

# Install yq (YAML processor)
ENV YQ_VERSION=4.44.6
RUN set -eux; \
    ARCH=$(dpkg --print-architecture); \
    if [ "$ARCH" = "amd64" ]; then YQ_ARCH="amd64"; \
    elif [ "$ARCH" = "arm64" ]; then YQ_ARCH="arm64"; \
    else echo "Unsupported arch: $ARCH" && exit 1; fi; \
    wget -O /usr/local/bin/yq \
      "https://github.com/mikefarah/yq/releases/download/v${YQ_VERSION}/yq_linux_${YQ_ARCH}"; \
    chmod +x /usr/local/bin/yq

# Set up non-root user
USER $USERNAME

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin:/home/$USERNAME/scripts

# Set the default shell to zsh rather than sh
ENV SHELL=/bin/zsh

# Set umask to allow group write permissions
ENV UMASK=0002

# Set the default editor and visual
ENV EDITOR=vim
ENV VISUAL=vim

# Set DOCKER_CONFIG to ensure Docker config files are created with correct ownership
ENV DOCKER_CONFIG=/home/claude/.docker

# Install Oh My Zsh and plugins
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended && \
    git clone https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k && \
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions && \
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting

# Install tmux plugin manager
RUN git clone https://github.com/tmux-plugins/tpm /home/$USERNAME/.tmux/plugins/tpm

# Install Claude Code and related tools/mcp servers etc
# https://github.com/anthropics/claude-code
# https://github.com/ryoppippi/ccusage
# https://github.com/upstash/context7
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} \
    && npm install -g ccusage \
    && claude mcp add context7 -- npx -y @upstash/context7-mcp

# Install Codex CLI
RUN npm install -g @openai/codex

# Install tmux plugins
RUN /home/$USERNAME/.tmux/plugins/tpm/bin/install_plugins || true

# Copy all scripts with proper permissions (including subdirectories)
COPY --chown=$USERNAME:$USERNAME --chmod=755 devcontainer-base/scripts/*.sh /home/$USERNAME/scripts/

# Copy claude defaults
COPY --chown=$USERNAME:$USERNAME devcontainer-base/claude-defaults /home/$USERNAME/claude-defaults

# Copy configuration files
COPY --chown=$USERNAME:$USERNAME devcontainer-base/conf/.zshrc /home/$USERNAME/.zshrc
COPY --chown=$USERNAME:$USERNAME devcontainer-base/conf/.tmux.conf /home/$USERNAME/.tmux.conf
COPY --chown=$USERNAME:$USERNAME devcontainer-base/conf/codex_config.toml /home/$USERNAME/.codex/config.toml

# Create logs directory for scripts to avoid conflicts with .ai_agents_sandbox directory
RUN mkdir -p /home/$USERNAME/scripts/logs && \
    chown -R $USERNAME:$USERNAME /home/$USERNAME/scripts/logs

# Copy default whitelist from common_settings
COPY common-settings/default-whitelist.txt /usr/local/etc/default-whitelist.txt

# Copy entrypoint script
COPY --chown=claude:local-ai-team devcontainer-base/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["sleep", "infinity"]
