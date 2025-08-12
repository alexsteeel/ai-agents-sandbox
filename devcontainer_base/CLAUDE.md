# devcontainer_base/CLAUDE.md

This directory contains the foundation Docker image for secure devcontainer environments.

## Purpose

Provides a reusable base image with:
- Non-root user setup (claude:dev)
- Development tools (Node.js, Python/uv, Docker CLI)
- Security controls and network isolation support
- Claude Code defaults and linting hooks
- Testing utilities for validation

## Build Process

The base image is built using:
```bash
./build.sh  # Builds claudecode/devcontainer:latest
```

## Directory Structure

### `/scripts/`
Security and setup scripts installed in the image:

- **`get-whitelist.sh`**: Merges whitelist files from multiple sources
  - Combines built-in defaults with project-specific domains
  - Outputs merged list for tinyproxy configuration
  
- **`non-root-post-create.sh`**: Post-creation setup for non-root user
  - Sets up Docker certificates for DinD
  - Configures Claude Code settings
  - Initializes development environment
  - Creates logs in `~/scripts/logs/` to avoid conflicts with `.claude/` directory

- **`setup-claude-defaults.sh`**: Installs Claude Code configurations
  - Copies agent definitions to `.claude/agents/`
  - Sets up linting hooks in `.claude/hooks/`
  - Configures default settings
  - Handles ownership gracefully, excluding `logs/` and `projects/` directories

- **`setup-p10k.sh`**: Configures Powerlevel10k theme for zsh
  - Interactive theme configuration
  - Terminal appearance customization

- **`test-network.sh`**: Network isolation verification
  - Tests proxy-only access enforcement
  - Validates DNS blocking without proxy
  - Verifies whitelist filtering

- **`test-permissions.sh`**: Security permissions validation
  - Confirms non-root user enforcement
  - Checks file ownership and permissions
  - Validates security constraints
  - Verifies `/workspace/projects` directory has group `dev` for shared access

- **`test-tools.sh`**: Development tools verification
  - Tests all installed tools and versions
  - Validates Python, Node.js, Docker CLI
  - Checks linters and formatters

### `/claude-defaults/`
Default Claude Code configurations:

- **`/agents/`**: Pre-configured AI agent definitions (6 total)
  - `analytics.md`: Data analytics and visualization
  - `code-reviewer.md`: Code review and quality assurance
  - `data-engineering-lead.md`: Architecture guidance
  - `python-data-engineer.md`: Data pipeline development
  - `python-qa-engineer.md`: Testing and QA
  - `senior-devops-engineer.md`: Infrastructure

- **`/hooks/`**: Linting and validation hooks
  - `lint_common.py`: Shell, Docker, YAML linting
  - `lint_python.py`: Python code quality checks

- **`settings.json`**: Default Claude Code settings

### `/conf/`
User configuration files:
- `.tmux.conf`: Terminal multiplexer configuration
- `.zshrc`: Shell configuration with p10k theme

### `default-whitelist.txt`
Built-in allowed domains for proxy filtering:
- Package registries (npm, pip, etc.)
- Source control (GitHub, GitLab)
- Development tools and documentation

## Docker Image Details

**Base**: Ubuntu 22.04
**User**: claude (UID 1001)
**Group**: dev (GID 2000)
**Shell**: zsh with Powerlevel10k

**Installed Tools**:
- Node.js 20 LTS
- Python with uv package manager
- Docker CLI (for DinD connection)
- Git and development utilities
- Linters: shellcheck, hadolint, yamllint, ruff, black

**Directory Structure**:
- `/home/claude/scripts/`: Utility scripts and tools (added to PATH)
- `/home/claude/scripts/logs/`: Script execution logs (separate from .claude/)
- `/home/claude/claude-defaults/`: Source for Claude Code configurations
- `/home/claude/.claude/`: Runtime Claude Code configuration (populated by setup script)
- `/home/claude/.claude/projects/`: Mount point for host projects directory (group: dev)

## Security Constraints

The image enforces:
- **NO root access**: User 'claude' has no sudo
- **NO passwords**: No authentication mechanisms
- **NO SSH**: No remote access services
- **File permissions**: Strict ownership model
- **Network isolation ready**: Designed for internal networks

## Container Lifecycle Scripts

### `entrypoint.sh` (Runtime)
- **When**: Runs every time the container starts
- **Purpose**: Runtime initialization and fixes
- **Tasks**:
  - Fixes `.codex` directory ownership issues
  - Sets up `.zsh_history` persistence with symlinks
  - Ensures proper file permissions for runtime

### `non-root-post-create.sh` (Post-Creation)
- **When**: Runs once after container is first created
- **Purpose**: One-time setup and validation
- **Tasks**:
  - Orchestrates all setup scripts (P10k, Claude defaults)
  - Runs comprehensive test suites
  - Creates logs in `~/scripts/logs/`
  - Provides setup summary

## Testing

After building, run validation tests:
```bash
docker run --rm claudecode/devcontainer:latest /usr/local/bin/test-tools.sh
docker run --rm claudecode/devcontainer:latest /usr/local/bin/test-permissions.sh
```

Network tests require proper compose setup:
```bash
# From .devcontainer/ directory with compose running
docker exec devcontainer /usr/local/bin/test-network.sh
```

## Extending the Base Image

Projects can extend this base:
```dockerfile
FROM claudecode/devcontainer:latest
# Add project-specific tools
USER claude
WORKDIR /workspace
```

Remember: Maintain security constraints when extending.