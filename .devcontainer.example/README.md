# DevContainer Example Template

This directory contains a complete example of a devcontainer setup using the AI Agents Sandbox foundation.

## Quick Start

1. **Copy this directory to your project:**
   ```bash
   cp -r .devcontainer.example /path/to/your-project/.devcontainer
   ```

2. **Initialize the project:**
   ```bash
   cd /path/to/your-project
   ai-sbx-init-project .
   ```
   This will:
   - Set up proper permissions
   - Generate `.env` with project paths
   - Configure Docker registry for cache sharing

3. **Open in your IDE:**
   - **VS Code**: Open folder, select "Reopen in Container"
   - **PyCharm**: Configure Docker Compose interpreter
   - **Claude Code**: Run `claude --dangerously-skip-permissions`

## Files

### Required Files

- **`docker-compose.yaml`** - Includes base template and overrides
- **`.gitignore`** - Excludes local configuration files

### Optional Files

- **`override.yaml`** - Project-wide customizations (committed to git)
- **`override.user.yaml`** - Machine-specific settings (gitignored, user-created)
- **`Dockerfile`** - Only if extending the base image
- **`devcontainer.json`** - VS Code configuration
- **`.env`** - Local environment variables (gitignored, auto-generated)

## Configuration

### Whitelist Domains

Edit `override.yaml` to add project-specific domains:

```yaml
services:
  tinyproxy-devcontainer:
    environment:
      USER_WHITELIST_DOMAINS: api.myproject.com,cdn.myproject.com
  
  tinyproxy-dind:
    environment:
      USER_WHITELIST_DOMAINS: private.registry.com
```

### Corporate Proxy

Set in `.env` file:
```bash
UPSTREAM_PROXY=http://proxy.company.com:3128
NO_UPSTREAM=internal.company.com,*.local
```

### Custom Tools

Extend the base image in `Dockerfile`:
```dockerfile
FROM ai-agents-sandbox/devcontainer:latest
USER claude
RUN pip install --user mypackage
```

## Security Notes

- **Never** change `internal: true` networks
- **Never** add sudo or root access
- **Never** commit `.env` or `override.user.yaml`
- Keep sensitive data in `.env` file
- Use read-only mounts for configs

## Troubleshooting

### Permission Denied
Run `ai-sbx-init-project` to fix permissions

### Proxy Issues
Check `USER_WHITELIST_DOMAINS` in override.yaml

### Docker Cache Not Working
Run `ai-sbx-init-project` to configure the local registry

### Can't Connect to Container
Ensure Docker service is running: `docker ps`