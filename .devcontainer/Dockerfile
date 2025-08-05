FROM node:20

ARG TZ
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest

# Install basic development tools and iptables/ipset
RUN apt-get update && apt-get install -y --no-install-recommends \
  less \
  git \
  procps \
  sudo \
  fzf \
  zsh \
  man-db \
  unzip \
  gnupg2 \
  gh \
  iptables \
  ipset \
  iproute2 \
  dnsutils \
  aggregate \
  jq \
  vim \
  tmux \
  fonts-powerline \
  locales \
  wget \
  ca-certificates \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Docker CLI only
RUN apt-get update && apt-get install -y lsb-release \
  && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
  && apt-get update \
  && apt-get install -y docker-ce-cli \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

ARG USERNAME=claude
ARG USER_UID=1001
ARG USER_GID=$USER_UID
ARG WORKSPACE_GID=2000
ARG PASSWORD=claude

RUN groupadd --gid 1001 claude \
 && groupadd --gid 2000 dev \
 && useradd --uid 1001 --gid 2000 -m claude \
 && echo "claude:claude" | chpasswd \
 && usermod -aG sudo claude \
 && echo "claude ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/claude \
 && chmod 0440 /etc/sudoers.d/claude

# Add node user to docker group
RUN usermod -aG docker $USERNAME || true

# Generate locale
RUN locale-gen en_US.UTF-8

# Ensure default user has access to /usr/local/share
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
RUN mkdir -p /workspace /home/$USERNAME/.claude && \
  chown -R $USERNAME:$USERNAME /workspace /home/$USERNAME/.claude

WORKDIR /workspace

ARG GIT_DELTA_VERSION=0.18.2
RUN ARCH=$(dpkg --print-architecture) && \
  wget "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  sudo dpkg -i "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb" && \
  rm "git-delta_${GIT_DELTA_VERSION}_${ARCH}.deb"

# Set up non-root user
USER $USERNAME

# Install global packages
ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin

# Set the default shell to zsh rather than sh
ENV SHELL=/bin/zsh

# Set the default editor and visual
ENV EDITOR=vim
ENV VISUAL=vim

# Install Oh My Zsh and plugins
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended && \
    git clone https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k && \
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-autosuggestions && \
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting

# Copy configuration files
COPY --chown=$USERNAME:$USERNAME .zshrc /home/$USERNAME/.zshrc
COPY --chown=$USERNAME:$USERNAME .tmux.conf /home/$USERNAME/.tmux.conf
COPY --chown=$USERNAME:$USERNAME .p10k.zsh /home/$USERNAME/.p10k.zsh

# Install tmux plugin manager
RUN git clone https://github.com/tmux-plugins/tpm /home/$USERNAME/.tmux/plugins/tpm

# Install Claude
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

# Install tmux plugins
RUN /home/$USERNAME/.tmux/plugins/tpm/bin/install_plugins || true

USER root

# Set zsh as the default shell
RUN chsh -s /usr/bin/zsh $USERNAME

# Copy and set up firewall script
COPY init-firewall.sh /usr/local/bin/

ONBUILD COPY allowed-domains.txt /usr/local/etc/
ONBUILD RUN chmod +x /usr/local/bin/init-firewall.sh && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh -d /usr/local/etc/allowed-domains.txt" > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall