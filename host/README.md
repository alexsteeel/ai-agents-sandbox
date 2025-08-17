# Host Scripts

Minimal set of helper scripts for AI Agents Sandbox environments.

## Installation

```bash
sudo ./install.sh
```

Installs two commands system-wide:

## Available Commands

### `ai-sbx-create-task-worktree`
Creates a git worktree for a new task.

```bash
ai-sbx-create-task-worktree "feature 123 implement user auth"
```

Automatically:
1. Creates worktree: `../feature-123-implement-user-auth`
2. Creates branch: `feature-123-implement-user-auth`
3. Creates: `tasks/feature-123-implement-user-auth/initial_requirements.md`
4. Opens PyCharm (if available)

### `ai-sbx-notify-watch`
Optional notification watcher for desktop alerts.

```bash
ai-sbx-notify-watch &
```

Shows desktop notifications when containers need attention.

## How Projects Work

### Setup Requirements

Your project needs a `.devcontainer/` folder with:
- `docker-compose.yaml` - Includes the base template
- `override.yaml` - Your customizations (optional)
- `.env` - Project settings
- `whitelist.txt` - Allowed domains
- `dind-whitelist.txt` - Docker registries
- `Dockerfile` - Custom image (optional)
- `devcontainer.json` - VS Code configuration

**This repository already has these files ready to use!**

For new projects, copy from `.devcontainer.example/`.

### For PyCharm:
1. Open project in PyCharm
2. Settings → Project → Python Interpreter → Add → Docker Compose
3. Select service: `devcontainer`
4. PyCharm handles starting/stopping containers

### For VS Code:
1. Open project in VS Code
2. Click "Reopen in Container" when prompted
3. VS Code handles everything

### For Claude Code:
Just run `claude --dangerously-skip-permissions` - no container needed.

## What the Installer Does

The `install.sh` script:
1. Installs the two helper scripts to `/usr/local/bin`
2. Creates the `local-ai-team` group (GID 2000) for file sharing
3. Creates `~/.ai_agents_sandbox/notifications` for container alerts
4. Creates `~/.ai_agents_sandbox/projects` for cross-project statistics
5. Installs the base Docker Compose template to `/usr/local/share/ai-agents-sandbox`

## Philosophy

- **Projects own their configuration** - `.devcontainer/` is in the repo
- **IDEs manage containers** - No manual start/stop needed
- **Minimal scripts** - Only what adds real value
- **No unnecessary abstractions** - Use IDE features directly