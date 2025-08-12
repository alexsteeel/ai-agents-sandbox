# Isolated AI Development Environments

> ⚠️ **This system is under active development** - expect frequent updates and improvements.

This repository is a **foundation** (with a **full working example**) for per-task, **agent-centric** development.
It lets you run several tasks **in parallel**, each in its **own isolated environment**.

## What it does

* **Per-task isolation.** Each task lives in its own Git **worktree** with its own containers and network.
* **Agent-centric workflow.** The **AI agents** run **together** in the same sandbox (Claude Code, Codex CLI, Gemini CLI …).
* **Pluggable services.** Start the services you need (DBs, object storage, caches, brokers, vector stores, …).
* **Highly customizable.** Swap agents, services, env vars, and compose files without modifying the base.

## Security model

* **Non-root users.** Default user inside containers is **non-root** (user: claude, UID: 1001).
  * **Write access only to:** the **workspace** and the user's **home directory**.
  * No write access elsewhere; **no `sudo`** in images.
  * Group `dev` (GID: 2000) for shared file access between host and container.

* **Restricted networking.** **Default-deny egress**; outbound HTTP/HTTPS goes through **Tinyproxy** with whitelist filtering.
  * **Upstream proxy support:** Optional SOCKS5/HTTP upstream proxy for additional routing (e.g., SSH tunnels).
  * **Dual proxy setup:** Separate proxies for devcontainer and Docker-in-Docker with different whitelists.

* **Isolated Docker.** Docker-in-Docker is **network-isolated** and constrained; it cannot access host Docker or host files.

* **Constrained devcontainer.** Minimal capabilities and internal networking only.

* **Parallel safety.** Multiple environments run side-by-side **without colliding** over resources, tables, or dashboards.

* **Host notifications.** Secure notification system using mounted volumes for container-to-host alerts.

---

# Architecture — Components & Networks

<img src="docs/architecture.png" alt="Architecture" title="Architecture" height="80%" />

---

# AI Agents

Pre-configured agents included in the base image:

```mermaid
flowchart TD
    TL["Technical Lead<br/>Architecture design<br/>Task planning & routing<br/>Team coordination"]

    AN["Analytics Engineer<br/>Requirements analysis<br/>Data exploration<br/>Metrics design"]

    SE["Software Engineer<br/>API development<br/>Business logic<br/>Performance optimization"]

    QA["QA Engineer<br/>Test creation & review<br/>Test automation<br/>Quality assurance"]

    CR["Code Reviewer<br/>Automated code review<br/>Uses Codex CLI<br/>Quality analysis"]

    TW["Technical Writer<br/>Documentation<br/>API docs, guides<br/>README files"]

    DO["Senior DevOps<br/>Infrastructure<br/>CI/CD pipelines<br/>Container orchestration"]

    TL <--> AN
    TL --> SE
    TL --> QA
    SE <--> QA
    SE <--> CR
    TL --> TW
    TL --> DO
    AN --> SE
    QA --> CR
```

---

# Parallel Tasks — Multi-Environment Workflow

```mermaid
flowchart TD
    subgraph E1 ["Environment 1"]
        CC1["Claude Code<br/>Team of agents"]
    end

    subgraph E2 ["Environment 2"]
        CC2["Claude Code<br/>Team of agents"]
    end

    subgraph E3 ["Environment 3"]
        CC3["Claude Code<br/>Team of agents"]
    end

    subgraph ME ["Master environment"]
        CCM["Claude Code<br/>Team of agents"]
    end

    CC1 -->|git worktree 1| REPO[Repository]
    CC2 -->|git worktree 2| REPO
    CC3 -->|git worktree 3| REPO

    REPO -->|Check and merge<br/>to main| CCM
```

---

## Quick start

### One-Time Setup (System-wide Installation)

```bash
# Install everything (builds images + installs management commands)
./install.sh

# This installs these commands system-wide:
# - claude-devcontainer: Main management command
# - claude-workspace-init: Initialize workspace
# - claude-notify-watch: Host notification watcher
# - claude-proxy-manager: Proxy configuration utility
```

### Using in Your Project

1. Initialize your project with the devcontainer:
   ```bash
   # From your project directory
   claude-devcontainer init
   # Or specify a path:
   claude-devcontainer init /path/to/project
   ```

2. Configure environment (optional):
   ```bash
   cd .devcontainer
   # Edit .env for proxy settings if needed
   vim .env
   # Add project-specific domains to whitelist.txt
   vim whitelist.txt
   ```

3. Start the environment:
   ```bash
   claude-devcontainer start
   ```

4. Create a task environment (worktree) for parallel work:
   ```bash
   # from your main repo
   git worktree add ../task-foo -b feature/task-foo
   cd ../task-foo
   claude-devcontainer init  # Initialize this worktree too
   claude-devcontainer start
   ```

5. Open in your IDE:
   - **VS Code:** Automatically detects `.devcontainer/devcontainer.json`
   - **PyCharm:** Open folder → Docker service will be detected
   - **Claude Code:** Run `claude --dangerously-skip-permissions`

### Management Commands

```bash
# Available commands after installation:
claude-devcontainer status     # Check container status
claude-devcontainer logs       # View logs
claude-devcontainer shell      # Open shell in container
claude-devcontainer stop       # Stop containers
claude-devcontainer clean      # Remove containers
claude-devcontainer validate   # Run security validation
```

## Network Configuration

### Proxy Filtering
- **Tinyproxy** enforces whitelist-based filtering (default-deny)
- Default whitelisted domains in `images/common-settings/default-whitelist.txt`:
  - GitHub, GitLab, PyPI, npm registry, JetBrains services
- Add project-specific domains to `.devcontainer/whitelist.txt`

### Upstream Proxy Support
Configure optional upstream proxy in `.devcontainer/.env`:

```bash
# Simple format - just specify proxy URL
UPSTREAM_PROXY=socks5://host.docker.internal:8900
# or
UPSTREAM_PROXY=http://host.docker.internal:3128

# Domains that bypass the upstream proxy
NO_UPSTREAM=github.com,gitlab.com
```

For SSH tunnels:
```bash
ssh -D 0.0.0.0:8900 your-server  # Creates SOCKS5 proxy
```

### Testing Network
```bash
docker exec devcontainer /home/claude/scripts/test-network.sh
```

## Notification System

The environment includes a host notification system for alerts from Claude Code:

### Setup
1. Notification directory is created automatically during installation
2. Install inotify-tools for instant notifications:
   ```bash
   sudo apt-get install inotify-tools  # Debian/Ubuntu
   ```
3. Start the notification watcher on your host:
   ```bash
   claude-notify-watch  # Installed system-wide by ./install.sh
   ```

### How it works
- Claude Code writes notifications to `/home/claude/.claude/notifications` in container
- This is mounted to `$HOME/.claude/notifications` on host
- Host watcher monitors the directory and shows desktop alerts
- Supports different urgency levels (error, complete, clarification, approval, blocked)

### Testing
From within the container:
```bash
/home/claude/claude-defaults/hooks/notify.sh test "Hello from container!"
```

## Customize

* **Agents.** Install or swap agents (Claude Code, Codex CLI, Gemini CLI …).
* **Services.** Edit the *service compose* to add DBs, caches, brokers, vector stores, etc.
* **Policy.** Adjust the proxy whitelist and egress rules; keep default-deny for safety.
* **Overrides.** Use compose overrides and env files to tailor paths, volumes, and resources—while the user stays **non-root** with write access limited to **workspace + home**.

---

*This repository is the **foundation with a complete working example**. It’s minimal, portable, secure by default, and easy to extend for your agents and services.*