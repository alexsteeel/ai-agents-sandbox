# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository provides a **base devcontainer foundation** for secure, isolated development environments. 

- **images/**: Docker images for the devcontainer foundation and proxy services
  - **devcontainer-base/**: Reusable foundation with all tools, scripts, and security controls
  - **tinyproxy-extended/**: Custom tinyproxy with whitelist filtering
  - **tinyproxy-dind/**: Dedicated proxy for Docker-in-Docker
  - **common-settings/**: Shared configuration and whitelists
- **.devcontainer/**: Minimal example showing how users implement the foundation in their projects
- **docs/**: Documentation and notes
- **host/**: Host-side scripts and tools
- **claude/**: Claude-specific configurations (when present)

The foundation enforces strict network isolation with proxy-based egress control for AI-assisted coding.

## 🔒 CRITICAL SECURITY REQUIREMENTS

**NEVER compromise these security principles:**
- **Non-root user only**: Container runs as user 'claude' (UID 1001), NEVER add sudo or root access
- **Internal network isolation**: `internal: true` network - containers CANNOT access internet directly
- **Strict proxy isolation**: 
  - Devcontainer MUST ONLY use tinyproxy-devcontainer:8888
  - Docker service MUST ONLY use tinyproxy-dind:8888
  - NEVER allow cross-proxy access between services
- **No bypassing**: Containers cannot resolve DNS or connect without proxy
- **Default deny**: Only explicitly whitelisted domains in filter can be accessed
- **No passwords/SSH**: NEVER add SSH servers, passwords, or authentication bypasses

## Key Commands

### System-wide Installation (one-time setup)
```bash
# Install everything: builds images + installs management commands
./install.sh

# This installs system-wide commands:
# - ai-sbx-task-worktree: Create git worktree for new tasks
# - ai-sbx-notify-watch: Host notification watcher (optional)
```

### Manual Build (if needed)
```bash
# Build specific images manually:
./images/build.sh devcontainer   # Build devcontainer base image
./images/build.sh tinyproxy      # Build tinyproxy image
./images/build.sh tinyproxy-dind # Build tinyproxy-dind image
./images/build.sh all            # Build all images
```

### Using in Your Project

#### 1. Ensure `.devcontainer/` exists
- This repo already has it
- For new projects, copy from `.devcontainer.example/`

#### 2. Configure (optional)
```bash
cd .devcontainer
vim .env          # Set PROJECT_NAME, proxy settings
vim whitelist.txt # Add project-specific domains
```

#### 3. Open in IDE

**PyCharm:**
1. Open project folder in PyCharm
2. **File** → **Settings** → **Project** → **Python Interpreter**
3. Click gear ⚙️ → **Add** → **Docker Compose**
4. Configuration:
   - Configuration files: `.devcontainer/docker-compose.yaml`
   - Service: `devcontainer`
   - Python interpreter path: `/usr/local/bin/python`
5. Click **OK** - PyCharm starts containers automatically

**VS Code:**
1. Open project folder
2. Click "Reopen in Container" when prompted
3. VS Code handles everything

**Claude Code:**
```bash
claude --dangerously-skip-permissions
```

### Claude Code
```bash
# Start Claude Code with local permissions
claude --dangerously-skip-permissions

# Create isolated git worktree for new tasks (automated)
ai-sbx-task-worktree "feature 123 implement user auth"
# This creates worktree, task folder, and opens PyCharm

# Or manually:
git worktree add -b task-name ../project-name-task-name
git worktree list
```

### Linting and Code Quality

The environment includes automated linting hooks that run on task completion:

- **Shell scripts**: `shellcheck`, `shfmt`
- **Dockerfiles**: `hadolint`
- **YAML files**: `yamllint`
- **Python code**: `uvx ruff check .`, `uvx black --check .`

Linting results are logged to:
- `.ai_agents_sandbox/logs/linters_common.json`
- `.ai_agents_sandbox/logs/linters_python.json`

## Architecture

### Network Security Model

```
Internet ←→ [tinyproxy] ←→ [claude-external network]
                                         ↑
                                   (NO DIRECT ACCESS)
                                         ↓
                            [claude-internal network (internal: true)]
                                    ↓            ↓
                            [devcontainer]  [docker]
```

**Key Points:**
- `claude-internal`: **MUST** remain `internal: true` - blocks all direct internet access
- `claude-external`: Only for proxy service
- Containers on internal network can ONLY access internet through proxy
- DNS resolution blocked without proxy

### Container Structure

**Base Image (claudecode/devcontainer:latest)**
```
Built-in tools and scripts:
├── /usr/local/bin/devcontainer-init    # Initialization script
├── /usr/local/bin/proxy-manager        # Proxy configuration utility
├── /usr/local/share/devcontainer/      # Templates and defaults
├── /home/claude/claude-defaults/hooks/ # Claude Code hooks
│   └── notify.sh                       # Notification hook for host alerts
├── User: claude (UID 1001) - NON-ROOT ONLY
├── NO sudo, NO root access
├── Group: dev (GID 2000) for file sharing
└── Tools: Node.js 20, Python (uv), Docker CLI, linters
```

**Runtime Services**
```
tinyproxy (custom extended image)
├── ONLY gateway to internet
├── Port 8888
├── Default-deny filter policy
├── FilterDefaultDeny Yes
├── Dynamic configuration via entrypoint
├── Automatic upstream proxy support
└── Whitelisted domains merged from:
    ├── Built-in defaults (images/devcontainer-base/default-whitelist.txt)
    ├── Common settings (images/common-settings/default-whitelist.txt)
    └── Project-specific (.devcontainer/whitelist.txt)

devcontainer (from base image or extended)
├── Network: claude-internal (isolated)
├── All HTTP(S) via proxy environment variables
└── Runs devcontainer-init on startup

docker (Docker-in-Docker)
├── Network: claude-internal (isolated)
├── TLS certificates in ~/.claude-docker-certs
└── Docker daemon for container operations
```

### IDE Integration (PyCharm/VS Code)

**How IDEs connect WITHOUT breaking security:**
- Define devcontainer as a service in docker-compose.yaml
- IDE connects via Docker daemon API (`docker exec`), NOT network
- Container remains on internal network
- Security model preserved

**VS Code:** 
- Automatically detects `.devcontainer/devcontainer.json`
- Handles container lifecycle automatically
- No manual configuration needed

**PyCharm:** 
- Uses Docker Compose service configuration
- Python interpreter: `/usr/local/bin/python`
- Service name: `devcontainer`
- Manages container lifecycle automatically
- Supports debugging, terminal, and file sync

### Proxy Configuration

**Adding whitelisted domains:**
Edit `.devcontainer/whitelist.txt` (one domain per line)

**Default whitelisted domains:**
- GitHub: github.com, raw.githubusercontent.com, github.githubassets.com
- Package registries: pypi.org, files.pythonhosted.org, registry.npmjs.org
- Dev tools: gitlab.com, bitbucket.org

**Upstream Proxy Support:**
The custom tinyproxy image supports automatic upstream proxy configuration:
- **Simple Format**: Set `UPSTREAM_PROXY=protocol://host:port` in `.env` file
- **Supported Protocols**: `http://` or `socks5://`
- **Bypass Domains**: Set `NO_UPSTREAM` to specify domains that bypass the upstream proxy
- The proxy configuration is automatically applied on container startup

**Environment Variables (.env):**
```bash
# Simplified upstream proxy configuration
UPSTREAM_PROXY=socks5://host.gateway:8900
# or
UPSTREAM_PROXY=http://proxy.example.com:3128

# Optional: Domains that bypass upstream proxy (space or comma separated)
NO_UPSTREAM=github.com,gitlab.com,bitbucket.org
```

**Verification commands:**
```bash
# Test that container CANNOT bypass proxy
docker exec <container> sh -c 'unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && curl https://google.com'
# Should fail with: Could not resolve host

# Test that proxy filtering works
docker exec <container> curl https://github.com  # Should work (whitelisted)
docker exec <container> curl https://evil.com    # Should fail (not in whitelist)
```

### AI Agents
Pre-configured agents built into the base image:
- `analytics-engineer.md`: Requirements analysis and data exploration
- `code-reviewer.md`: Automated code review with Codex
- `qa-engineer.md`: Quality assurance and testing
- `software-engineer.md`: Software development and API design
- `technical-lead.md`: Technical architecture and team coordination
- `technical-writer.md`: Technical documentation
- `senior-devops-engineer.md`: Infrastructure and DevOps

## Development Workflow

1. **System setup** (once): `sudo ./install.sh`
2. **Open project in IDE**:
   - **PyCharm**: Add Docker Compose interpreter
   - **VS Code**: Reopen in Container
3. **Create tasks** (optional): `ai-sbx-task-worktree "task description"`
4. **IDE manages containers**: No manual start/stop needed
5. **Security is automatic**: Internal network + proxy filtering

## Important Security Notes

⚠️ **NEVER DO THESE:**
- Add `sudo` to containers
- Install SSH servers
- Change `internal: true` to `internal: false`
- Add passwords or authentication
- Expose container ports directly
- Allow root user access
- Bypass proxy settings

✅ **ALWAYS MAINTAIN:**
- Non-root user (claude)
- Internal network isolation
- Proxy-only internet access
- Default-deny filtering
- Minimal container privileges

## Troubleshooting

**Container can access forbidden sites:**
- Check network: Must be `internal: true`
- Verify proxy env vars are set
- Ensure no direct network routes exist

**IDE cannot connect:**
- Use docker-compose-dev.yaml approach
- Ensure Docker daemon is accessible
- Check container is running: `docker ps`

**Proxy not working:**
- Check tinyproxy logs: `docker logs tinyproxy`
- Verify filter file exists and is correct
- Ensure proxy environment variables are set

**Claude agents not appearing:**
- Run setup script: `~/scripts/setup-claude-defaults.sh`
- Check for log conflicts in `~/.ai_agents_sandbox/logs/`
- Verify all 6 agents exist in `/home/claude/claude-defaults/agents/`
- Logs should be in `~/scripts/logs/` not `~/.ai_agents_sandbox/logs/`

**Building Docker images from devcontainer:**
- Add Docker registry domains to `.devcontainer/whitelist.txt`:
  - docker.io, registry-1.docker.io, auth.docker.io, hub.docker.com
- Or use the Docker daemon via docker-in-docker service
- The dind proxy has separate whitelist in `dind-whitelist.txt`

Remember: Security is paramount. When in doubt, choose the more restrictive option.

## Projects Directory Mount

The `.ai_agents_sandbox/projects` directory is mounted from the host system to enable cross-project statistics and analysis. This allows tools like `ccusage` to aggregate metrics across all projects in a single location.

## Notification System

The devcontainer includes a notification system for alerting the host when Claude needs attention:

### How it works
1. **Container hook** (`/home/claude/claude-defaults/hooks/notify.sh`) writes notifications to `/home/claude/.ai_agents_sandbox/notifications/`
2. **Volume mount** maps `$HOME/.ai_agents_sandbox/notifications` (host) to `/home/claude/.ai_agents_sandbox/notifications` (container)
3. **Host watcher** (`ai-sbx-notify-watch`) monitors for notifications and displays desktop alerts

### Setup
1. **Installation**: Run `./install.sh` to install system-wide commands including notification watcher
2. **Start watcher**: Run `ai-sbx-notify-watch` on host for desktop notifications (installed system-wide)
3. **Fast mode**: Install `inotify-tools` on host for instant notifications:
   ```bash
   sudo apt-get install inotify-tools  # Debian/Ubuntu
   ```

### Notification Types
- **critical** urgency: error, clarification, blocked, approval
- **normal** urgency: general notifications
- **low** urgency: task completion

### Testing
From within container:
```bash
/home/claude/claude-defaults/hooks/notify.sh "test" "Your message here"
```
- no need in backward compatibility, it is new project