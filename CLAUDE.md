# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository provides a **base devcontainer foundation** for secure, isolated development environments. 

- **devcontainer_base/**: Reusable foundation with all tools, scripts, and security controls baked into the Docker image
- **.devcontainer/**: Minimal example showing how users implement the foundation in their projects

The foundation enforces strict network isolation with proxy-based egress control for AI-assisted coding.

## 🔒 CRITICAL SECURITY REQUIREMENTS

**NEVER compromise these security principles:**
- **Non-root user only**: Container runs as user 'claude' (UID 1001), NEVER add sudo or root access
- **Internal network isolation**: `internal: true` network - containers CANNOT access internet directly
- **Proxy-only egress**: ALL outbound traffic MUST go through Tinyproxy (port 8888)
- **No bypassing**: Containers cannot resolve DNS or connect without proxy
- **Default deny**: Only explicitly whitelisted domains in filter can be accessed
- **No passwords/SSH**: NEVER add SSH servers, passwords, or authentication bypasses

## Key Commands

### Build Base Image (one-time setup)
```bash
# Build the foundation Docker image (includes custom tinyproxy)
./build.sh
# Or manually:
cd devcontainer_base && ./build.sh
```

### Using in Your Project
```bash
# Copy minimal .devcontainer to your project
cp -r .devcontainer /path/to/your-project/

# Copy and customize environment variables
cd /path/to/your-project/.devcontainer
cp .env.example .env

# Initialize environment (first time only)
./initialize.sh /path/to/your-project

# Start services
docker compose up -d

# Stop services
docker compose down
```

### Claude Code
```bash
# Start Claude Code with local permissions
claude --dangerously-skip-permissions

# Create isolated git worktree for new tasks
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
- `.claude/logs/linters_common.json`
- `.claude/logs/linters_python.json`

## Architecture

### Network Security Model

```
Internet ←→ [tinyproxy] ←→ [claude-external network]
                                         ↑
                                   (NO DIRECT ACCESS)
                                         ↓
                            [claude-internal network (internal: true)]
                                    ↓            ↓
                            [devcontainer]  [docker-dind]
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
    ├── Built-in defaults (devcontainer_base/default-whitelist.txt)
    ├── Common settings (common_settings/default-whitelist.txt)
    └── Project-specific (.devcontainer/whitelist.txt)

devcontainer (from base image or extended)
├── Network: claude-internal (isolated)
├── All HTTP(S) via proxy environment variables
└── Runs devcontainer-init on startup

docker-dind (Docker-in-Docker)
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

**VS Code:** Automatically detects .devcontainer/devcontainer.json

**PyCharm:** Use docker-compose service approach
- Python interpreter: `/usr/local/bin/python`

### Proxy Configuration

**Adding whitelisted domains:**
Edit `.devcontainer/whitelist.txt` (one domain per line)

**Default whitelisted domains:**
- GitHub: github.com, raw.githubusercontent.com, github.githubassets.com
- Package registries: pypi.org, files.pythonhosted.org, registry.npmjs.org
- Dev tools: gitlab.com, bitbucket.org

**Upstream Proxy Support:**
The custom tinyproxy image supports automatic upstream HTTP proxy configuration via environment variables:
- Set `UPSTREAM_PROXY_HOST` and `UPSTREAM_PROXY_PORT` in `.env` file
- The proxy configuration is automatically applied on container startup
- SOCKS5 upstream proxies are not supported (tinyproxy limitation)

**Environment Variables (.env):**
```bash
# Optional: External HTTP proxy
UPSTREAM_PROXY_HOST=proxy.example.com
UPSTREAM_PROXY_PORT=3128
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
- `python-data-engineer.md`: ETL and data pipeline development
- `data-engineering-lead.md`: Technical architecture and leadership
- `python-qa-engineer.md`: Quality assurance and testing
- `senior-devops-engineer.md`: Infrastructure and DevOps

## Development Workflow

1. **Build base image**: Run `./build.sh` from project root (builds both base image and custom tinyproxy)
2. **Copy .devcontainer**: Copy minimal template to your project
3. **Customize**: Edit `.devcontainer/whitelist.txt` and `.env` as needed
4. **Start services**: Run `docker compose up` from project directory
5. **IDE connection**: VS Code/PyCharm automatically connects via Docker
6. **Verify security**: Ensure containers cannot bypass proxy

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

Remember: Security is paramount. When in doubt, choose the more restrictive option.