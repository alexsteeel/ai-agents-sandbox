# Host Scripts Documentation

This directory contains scripts that run on the host system to support the devcontainer environment.

## Key Scripts

### `ai-sbx-init-project`
Initializes a project for use with AI Sandbox devcontainers.

**What it does:**
- Sets up proper group permissions (dev group, GID 2000)
- Creates/updates `.devcontainer/.env` with:
  - `PROJECT_NAME`: Based on directory basename
  - `PROJECT_DIR`: Absolute path to project
  - `COMPOSE_PROJECT_NAME`: Ensures unique Docker container names
- Creates user directories for notifications and projects
- Handles git worktree configurations
- Sets up directory inheritance (setgid) for collaborative development

**Usage:**
```bash
ai-sbx-init-project /path/to/project
# or from project directory:
ai-sbx-init-project
```

**Important:** This script ensures each project gets unique volume and container names, preventing conflicts between multiple projects using the same devcontainer foundation.

## Notification System

The notification system enables Claude Code running in containers to alert the host user when attention is needed.

### Architecture

```
Container                         Host
─────────                        ─────
notify.sh hook                   notify-watch.sh
     ↓                                ↑
writes to mounted volume         monitors directory
     ↓                                ↑
/workspace/.notifications  ←→  $HOME/.claude-notifications
                                      ↓
                                 Desktop notification
```

### Scripts

#### `notify-watch.sh`
Fast notification watcher using inotify (if available) or polling fallback.

**Features:**
- Instant notifications with inotify
- Fallback to 0.2s polling if inotify unavailable
- Desktop notifications via `notify-send`
- Urgency levels based on notification type
- Automatic file cleanup after processing

**Usage:**
```bash
./host-scripts/notify-watch.sh
```

**Dependencies:**
- **Required**: None (basic shell)
- **Recommended**: `inotify-tools` for instant notifications
- **Optional**: `notify-send` for desktop alerts

**Install dependencies:**
```bash
# Debian/Ubuntu
sudo apt-get install inotify-tools libnotify-bin

# RHEL/CentOS
sudo yum install inotify-tools libnotify

# macOS
brew install fswatch terminal-notifier
```

### Notification Types

The system supports different urgency levels:

| Type | Urgency | Use Case |
|------|---------|----------|
| error | critical | Errors requiring immediate attention |
| clarification | critical | User input needed |
| blocked | critical | Process blocked, needs intervention |
| approval | critical | Awaiting user approval |
| complete | low | Task completed successfully |
| test | normal | Testing notifications |
| attention | normal | General notifications |

### Setup Process

1. **Initialize permissions** (one-time):
   ```bash
   cd .devcontainer
   ./init-project.sh /path/to/project
   ```
   This creates `$HOME/.claude-notifications` with proper permissions.

2. **Start watcher** (each session):
   ```bash
   ./host-scripts/notify-watch.sh
   ```

3. **Test from container**:
   ```bash
   docker exec devcontainer /home/claude/claude-defaults/hooks/notify.sh "test" "Hello from container!"
   ```

### Troubleshooting

#### No notifications appearing
1. Check watcher is running: `ps aux | grep notify-watch`
2. Verify directory exists: `ls -la ~/.claude-notifications/`
3. Test write permissions: `touch ~/.claude-notifications/test.txt`
4. Check notify-send works: `notify-send "Test" "Message"`

#### Slow notifications
- Install inotify-tools for instant notifications
- Without inotify, polling occurs every 0.2 seconds
- Check CPU usage if polling is active

#### Permission errors
- Re-run initialize.sh to fix permissions
- Ensure you're in the `dev` group: `groups $USER`
- Directory should have group write permissions

### How It Works

1. **Container writes notification**:
   - Claude Code hooks call `/home/claude/claude-defaults/hooks/notify.sh`
   - Creates `notify.txt` in mounted volume
   - Logs to `log.txt` for history

2. **Host watcher detects file**:
   - inotifywait triggers on file creation (instant)
   - Or polling checks every 0.2s (fallback)
   - Reads and parses notification content

3. **Desktop alert displayed**:
   - Uses notify-send if available
   - Falls back to console output
   - Urgency level determines notification priority

4. **Cleanup**:
   - Notification file deleted after processing
   - Log file preserved for history

### Integration with Claude Code

Claude Code can trigger notifications through:
- Task completion hooks
- Error handlers
- User interaction requests
- Custom scripts

Example hook integration:
```bash
# In Claude Code hook
if [[ "$HOOK_TYPE" == "task-complete" ]]; then
    /home/claude/claude-defaults/hooks/notify.sh "complete" "Task finished: $TASK_NAME"
fi
```

### Security Considerations

- Notification directory is shared between host and container
- Only text files are written (no executable code)
- Files are immediately deleted after processing
- Directory has restricted permissions (dev group only)

### Future Enhancements

Potential improvements:
- Sound alerts for critical notifications
- Rich notification content (icons, actions)
- Notification history viewer
- Integration with system tray
- Cross-platform support (Windows, macOS)