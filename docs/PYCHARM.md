# PyCharm Setup Guide

Quick guide for using the AI Agents Sandbox with PyCharm.

## Prerequisites

1. PyCharm Professional (Community Edition doesn't support Docker)
2. Docker Desktop installed and running
3. Docker plugin enabled in PyCharm

## Initial Setup

### 1. System Installation (once per machine)

```bash
# From the ai_agents_sandbox repository
sudo ./install.sh
```

This builds Docker images and installs helper commands.

### 2. Ensure `.devcontainer/` Exists

Your project needs a `.devcontainer/` folder:
- **This repo**: Already has it, ready to use
- **New projects**: Copy from `.devcontainer.example/`
- Contains: docker-compose.yaml, whitelist.txt, Dockerfile, etc.

## PyCharm Configuration

### Step-by-Step

1. **Open your project** in PyCharm

2. **Open Settings**
   - Windows/Linux: `File` → `Settings`
   - macOS: `PyCharm` → `Preferences`

3. **Navigate to Python Interpreter**
   - `Project: [YourProject]` → `Python Interpreter`

4. **Add Docker Compose Interpreter**
   - Click the gear icon ⚙️ → `Add...`
   - Select `Docker Compose` from the left panel

5. **Configure the interpreter**:
   - **Server:** Docker (auto-detected)
   - **Configuration files:** Click folder icon and select `.devcontainer/docker-compose.yaml`
   - **Service:** `devcontainer`
   - **Environment variables:** Leave default
   - **Python interpreter path:** `/usr/local/bin/python`

6. **Click OK** and wait for PyCharm to:
   - Build the containers (first time only)
   - Start the services
   - Index the Python environment

## Using the Environment

### Automatic Container Management

PyCharm handles everything:
- **Starts containers** when you open the project
- **Stops containers** when you close PyCharm
- **Restarts containers** if configuration changes

### Running Code

- **Run configurations** execute inside the container
- **Debug** works seamlessly with breakpoints
- **Terminal** opens inside the container (`/workspace`)
- **Python Console** runs in the container context

### File Synchronization

- Files are mounted via Docker volumes
- Changes are instant in both directions
- No manual sync needed

## Working with Tasks

### Create a Task Worktree

```bash
# Creates git worktree + task folder + opens new PyCharm window
claude-task-worktree "feature 123 implement auth"
```

Each task gets:
- Separate git worktree
- Own container instance
- Isolated environment
- Task documentation folder

### Managing Multiple Tasks

- Each worktree can be opened in a separate PyCharm window
- Each has its own containers (no conflicts)
- Switch between tasks by switching PyCharm windows

## Customization

### Add Python Packages

Edit `.devcontainer/Dockerfile`:
```dockerfile
# Install additional packages
RUN pip install --user pandas numpy requests
```

### Add Whitelisted Domains

Edit `.devcontainer/whitelist.txt`:
```
api.myservice.com
auth.myservice.com
```

### Configure Proxy

Edit `.devcontainer/.env`:
```bash
# For corporate proxy
UPSTREAM_PROXY=http://corporate-proxy:8080

# For SSH tunnel
UPSTREAM_PROXY=socks5://host.docker.internal:8900
```

## Troubleshooting

### Container doesn't start

1. Check Docker Desktop is running
2. Verify Docker plugin is enabled in PyCharm
3. Check `.devcontainer/docker-compose.yaml` exists

### Import errors

1. Wait for PyCharm to finish indexing
2. Invalidate caches: `File` → `Invalidate Caches and Restart`

### Permission errors

The container runs as non-root user `claude` (UID 1001). Ensure your files are accessible to this user.

### View container logs

1. Open **Services** tool window (`View` → `Tool Windows` → `Services`)
2. Navigate to `Docker` → `Docker Compose` → Your project
3. Right-click container → `View Logs`

## Tips

1. **Performance**: Increase Docker Desktop memory allocation for better performance
2. **Multiple projects**: Each project gets unique container names (no conflicts)
3. **Debugging**: Set breakpoints normally - PyCharm handles the container connection
4. **Package management**: Use `pip install --user` or `uv` inside the container
5. **Environment variables**: Add to `.devcontainer/override.yaml` for persistence

## VS Code Comparison

Unlike VS Code which uses `devcontainer.json`, PyCharm:
- Uses Docker Compose service configuration directly
- Doesn't need special devcontainer extensions
- Provides full IDE features without configuration
- Handles multiple interpreters/projects better

## Quick Commands Reference

```bash
# Create task worktree
claude-task-worktree "task description"

# View running containers
docker ps

# Open shell manually (if needed)
docker exec -it PROJECT-devcontainer-1 /bin/zsh

# View logs
docker compose -p PROJECT logs -f devcontainer

# Stop everything manually (PyCharm does this automatically)
docker compose -p PROJECT down
```