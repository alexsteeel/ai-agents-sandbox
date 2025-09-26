# AI Agents Sandbox 🤖🔒

Secure Docker environments for AI-assisted coding with network isolation.

## Installation

```bash
git clone https://github.com/alexsteeel/ai-agents-sandbox.git
cd ai-agents-sandbox
pip install -e .
```

## Quick Start

```bash
# 1. One-time setup (builds images, creates group)
ai-sbx init global

# 2. Initialize your project
cd /path/to/your/project
ai-sbx init project

# 3. Create task worktree (automatically opens IDE)
ai-sbx worktree create "implement user authentication"

# Work on your task...

# 4. Clean up when done
ai-sbx worktree remove
```

## Features

- **Security:** Non-root containers, network isolation, proxy filtering
- **Per-task isolation:** Each task in its own git worktree
- **AI-ready:** Works with Claude Code, Codex, and other AI assistants
- **Auto IDE launch:** `worktree create` opens your preferred IDE automatically
- **Docker caching:** Built-in registry proxy for fast image pulls
- **Multiple environments:** Base, .NET, Go variants

## Commands

```bash
ai-sbx init global       # One-time system setup
ai-sbx init project      # Setup project with devcontainer
ai-sbx worktree create   # Create task workspace (opens IDE)
ai-sbx worktree list     # List workspaces
ai-sbx worktree remove   # Remove workspace
ai-sbx notify            # Watch for container notifications (run on host)
ai-sbx doctor --fix      # Fix common issues
```

## Documentation

- [Architecture — Components & Networks](docs/ARCHITECTURE.md)
- [Full documentation](docs/)

## Configuration

Run `ai-sbx init project` again to reconfigure:
- Whitelist domains
- Upstream proxy
- Custom registries
- Claude settings inclusion

Or manually edit `.devcontainer/ai-sbx.yaml` and run `ai-sbx init update`

## IDE Setup (if opening manually)

**VS Code:** Open folder → "Reopen in Container"

**PyCharm (DevContainer setup):**
When you open the project, it should automatically suggest loading in devcontainer. Alternative method:
- Right-click on .devcontainer.json file > Dev Containers > Create Devcontainer and mount sources > PyCharm
For other JetBrains IDEs, the process is similar

**Claude Code:** `claude --dangerously-skip-permissions`

## License

MIT