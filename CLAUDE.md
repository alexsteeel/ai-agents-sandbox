# AI Agents Sandbox

Secure Docker environments for AI-assisted coding with network isolation.

## Quick Start

### 1. Install
```bash
pip install -e .
ai-sbx init global --wizard  # Interactive setup with custom registry option
# OR
ai-sbx init global  # Basic setup (builds images, creates groups)
```

### 2. Setup Project
```bash
cd /your/project
ai-sbx init project

# Interactive wizard will:
# - Detect your Claude settings (~/.claude/) and offer to include them
# - Configure network isolation and proxy
# - Create .devcontainer for your IDE
```

### 3. Work on Tasks
```bash
# Create isolated workspace for a task
ai-sbx worktree create "implement user authentication"

# Open in your IDE (VS Code: "Reopen in Container", PyCharm: Docker Compose interpreter)
# Work on the task...

# Clean up when done
ai-sbx worktree remove
```

## Key Commands

```bash
ai-sbx init global --wizard # Interactive setup with detailed reporting
ai-sbx init project         # Setup project with devcontainer
ai-sbx worktree create      # Create task workspace
ai-sbx worktree list        # List workspaces
ai-sbx worktree remove      # Remove workspace
ai-sbx doctor --verbose     # Detailed system analysis
ai-sbx doctor --fix         # Fix common issues
```

### Init Global Reporting

The `init global` command now provides detailed reporting of all system changes:
- Directories created with full paths
- Files created or modified
- Docker images built
- System groups created
- User modifications
- Docker containers started
- Any errors encountered

This helps you understand exactly what changes are made to your system.

## Security Features

✅ **Built-in Protection:**
- Non-root container (user: claude)
- Network isolation (internal network)
- Proxy filtering (whitelisted domains only)
- No SSH, sudo, or passwords

⚠️ **Never:**
- Add sudo or root access
- Disable network isolation
- Bypass proxy settings

## IDE Setup

**VS Code:** Open folder → "Reopen in Container" when prompted

**PyCharm:** Settings → Python Interpreter → Add → Docker Compose
- Service: `devcontainer`
- Python path: `/usr/local/bin/python`

**Claude Code:** `claude --dangerously-skip-permissions`

## Claude Settings

During project setup, if you have `~/.claude/` on your host:
- The CLI detects your agents, commands, and hooks
- Choose to mount them (readonly) in the container
- Settings are copied on container startup (keeping originals safe)

## Custom Registry Configuration (Enterprise/Corporate Networks)

During `ai-sbx init global --wizard`:
- Configure custom Docker registries for caching (e.g., proget.company.com)
- Specify custom docker-registry-proxy image with embedded CA certificates
- Automatically creates `.env` file at `/usr/local/share/ai-agents-sandbox/docker-proxy/.env`

Example configuration:
```bash
# Custom registries (comma-separated)
registry1.company.com,registry2.local

# Custom proxy image with CA certificates
myregistry/docker-registry-proxy:custom-ca
```

## Enhanced Diagnostics

**Detailed system analysis:**
```bash
ai-sbx doctor --verbose  # Shows all system state, directories, files, containers
```

The doctor command now reports:
- All AI Agents Sandbox directories with permissions and sizes
- Configuration files status
- Docker containers state
- System groups and members
- Detailed issue analysis

## Troubleshooting

**Container can't access a site:** Add domain to `.devcontainer/ai-sbx.yaml` whitelist, run `ai-sbx init update`

**IDE can't connect:** Check Docker is running: `docker ps`

**Need upstream proxy:** Configure in `.devcontainer/ai-sbx.yaml`, run `ai-sbx init update`

**Custom registry issues:** Check `/usr/local/share/ai-agents-sandbox/docker-proxy/.env` exists and contains your registries

## Project Structure

```
your-project/
├── .devcontainer/
│   ├── ai-sbx.yaml         # Your configuration (edit this)
│   ├── .env                # Auto-generated (don't edit)
│   └── docker-compose.yaml # Container setup
└── your code...
```

---

For detailed documentation, see [docs/](docs/) directory.