# Development Guide

This guide is for developers working on the AI Agents Sandbox repository itself.

## Repository Structure

```
ai_agents_sandbox/
├── .devcontainer/          # Working devcontainer for this repo
├── .devcontainer.example/  # Template for new projects
├── images/                 # Docker image sources
│   ├── devcontainer-base/  # Base development image
│   ├── tinyproxy/ # Proxy with whitelist filtering
│   ├── tinyproxy-dind/     # Proxy for Docker-in-Docker
│   └── common-settings/    # Shared configurations
├── templates/              # System templates
│   └── docker-compose.base.yaml
├── host/                   # Host-side scripts
│   ├── install.sh          # System installer
│   ├── claude-task-worktree
│   └── claude-notify-watch
└── docs/                   # Documentation
```

## Working on This Repository

### Prerequisites

1. Docker Desktop installed and running
2. Git configured
3. PyCharm Professional or VS Code

### Setup for Development

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/ai_agents_sandbox.git
   cd ai_agents_sandbox
   ```

2. **Install system components (one-time):**
   ```bash
   sudo ./install.sh
   ```
   This builds all Docker images and installs helper scripts.

3. **Open in your IDE:**
   
   **PyCharm:**
   - Open the repository folder
   - Settings → Project → Python Interpreter
   - Add → Docker Compose
   - Configuration file: `.devcontainer/docker-compose.yaml`
   - Service: `devcontainer`
   - Python interpreter: `/usr/local/bin/python`
   
   **VS Code:**
   - Open the repository folder
   - Click "Reopen in Container" when prompted

### The `.devcontainer/` in This Repo

This repository already has a working `.devcontainer/` configuration:
- Uses the include pattern to reference the base template
- Has override.yaml for customizations
- Configured for development work on the sandbox itself

### Making Changes

#### To Docker Images

1. Edit files in `images/*/`
2. Rebuild with: `./images/build.sh [image-name]`
3. Test in the devcontainer

#### To Templates

1. Edit `templates/docker-compose.base.yaml`
2. Reinstall: `sudo ./host/install.sh`
3. Test with a new project

#### To Host Scripts

1. Edit scripts in `host/`
2. Reinstall: `sudo ./host/install.sh`
3. Test the commands

### Testing Changes

1. **Test in this repo's devcontainer:**
   - The `.devcontainer/` here uses the latest builds
   - Good for quick iteration

2. **Test in a new project:**
   ```bash
   # Create test project
   mkdir /tmp/test-project
   cp -r .devcontainer.example /tmp/test-project/.devcontainer
   cd /tmp/test-project
   # Open in IDE and test
   ```

3. **Test parallel tasks:**
   ```bash
   claude-task-worktree "test feature 123"
   ```

### Building and Tagging Images

```bash
# Build all images
./images/build.sh all

# Build specific image
./images/build.sh devcontainer

# Tag for release
docker tag ai-agents-sandbox/devcontainer:latest ai-agents-sandbox/devcontainer:1.0.0
```

### Release Process

1. Update version tags in:
   - `.devcontainer.example/override.yaml`
   - Documentation files

2. Build and tag images:
   ```bash
   ./images/build.sh all
   docker tag ai-agents-sandbox/devcontainer:latest ai-agents-sandbox/devcontainer:1.0.0
   docker tag tinyproxy:latest tinyproxy:1.0.0
   docker tag tinyproxy-dind:latest tinyproxy-dind:1.0.0
   ```

3. Update documentation:
   - README.md for user-facing changes
   - CHANGELOG.md for version history

4. Commit and tag:
   ```bash
   git add .
   git commit -m "Release v1.0.0"
   git tag v1.0.0
   git push origin main --tags
   ```

## Architecture Decisions

### Why Include Pattern?

The `docker-compose.yaml` uses Docker Compose's include feature:
```yaml
include:
  - path: /usr/local/share/ai-agents-sandbox/docker-compose.base.yaml
  - override.yaml
```

This allows:
- Central management of base configuration
- Easy updates without modifying projects
- Clean separation of concerns

### Why No Initialization Scripts?

We removed `claude-workspace-init` because:
- Projects should own their configuration
- IDEs handle container lifecycle perfectly
- Less abstraction = easier to understand
- Files in repo > generated files

### Security Model

Never compromise on:
- Non-root user (claude, UID 1001)
- Internal network isolation
- Proxy-only egress
- Default-deny filtering
- No sudo/SSH/passwords

## Troubleshooting Development

### Container won't build

```bash
# Clean rebuild
docker system prune -a
./images/build.sh all
```

### Changes not reflected

```bash
# Force recreate containers
docker compose down -v
docker compose up -d --force-recreate
```

### Permission issues

```bash
# Ensure dev group exists
sudo groupadd -g 2000 dev
sudo usermod -aG dev $USER
# Re-login for group changes
```

## Contributing

1. Keep security model intact
2. Maintain simplicity - less is more
3. Test in both VS Code and PyCharm
4. Document any new features
5. Update examples if needed