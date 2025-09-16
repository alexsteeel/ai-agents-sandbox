# AI Agents Sandbox

Secure Docker environments for AI-assisted coding with network isolation.

## Quick Start

### 1. Install
```bash
pip install -e .
ai-sbx init global  # One-time setup (builds images, creates groups)
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
ai-sbx init global          # One-time system setup
ai-sbx init project         # Setup project with devcontainer
ai-sbx worktree create      # Create task workspace
ai-sbx worktree list        # List workspaces
ai-sbx worktree remove      # Remove workspace
ai-sbx doctor --fix         # Fix common issues
```

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

## Troubleshooting

**Container can't access a site:** Add domain to `.devcontainer/ai-sbx.yaml` whitelist, run `ai-sbx init update`

**IDE can't connect:** Check Docker is running: `docker ps`

**Need upstream proxy:** Configure in `.devcontainer/ai-sbx.yaml`, run `ai-sbx init update`

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