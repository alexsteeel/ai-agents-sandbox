# .devcontainer/CLAUDE.md

This directory contains the minimal devcontainer implementation template using the secure foundation.

## Purpose

Provides a ready-to-use template that projects can copy and customize while maintaining security controls.

## Quick Start

```bash
# Copy to your project
cp -r .devcontainer /path/to/your-project/

# Configure environment
cd /path/to/your-project/.devcontainer
cp .env.example .env
# Edit .env as needed

# Initialize (first time only)
./initialize.sh /path/to/your-project

# Start services
docker compose up -d
```

## Configuration Files

### `.env.example` / `.env`
Environment configuration template:
```bash
# Project Configuration
PROJECT_NAME=myproject
PROJECT_DIR=/path/to/project

# Network Configuration
NETWORK_EXTERNAL=claude-external
NETWORK_INTERNAL=claude-internal

# Optional: External HTTP Proxy
UPSTREAM_PROXY_HOST=
UPSTREAM_PROXY_PORT=

# Container Users
CLAUDE_UID=1001
CLAUDE_GID=2000
```

**Important**: 
- Copy `.env.example` to `.env` before use
- `.env` is gitignored (contains local paths)
- Set `PROJECT_DIR` to your actual project path

### `docker-compose.yaml`
Orchestrates three services:

1. **tinyproxy**: Filtering proxy gateway
   - Network: claude-external (bridge)
   - Port: 8888
   - Image: claudecode/tinyproxy:latest

2. **devcontainer**: Development environment
   - Network: claude-internal (internal)
   - User: claude (non-root)
   - Proxy: All traffic via tinyproxy
   - Image: claudecode/devcontainer:latest or custom

3. **docker**: Docker daemon
   - Network: claude-internal (internal)
   - Privileged: Required for Docker-in-Docker
   - Certificates: Shared with devcontainer

### `devcontainer.json`
VS Code configuration:
- Service: Points to docker-compose service
- Features: Additional VS Code features
- Settings: Editor and terminal configuration
- Extensions: Recommended extensions
- Mounts: Source code and Docker socket

### `whitelist.txt`
Project-specific allowed domains:
```
# Project APIs
api.myproject.com
auth.myproject.com

# Project dependencies
cdn.myproject.com

# Docker registries (if building images from within devcontainer)
docker.io
registry-1.docker.io
auth.docker.io
hub.docker.com
```

Add one domain per line. Merged with defaults at runtime.

**Note**: Docker registry domains are needed only if you build Docker images from within the devcontainer. The docker-in-docker service has its own whitelist in `dind-whitelist.txt`.

### `initialize.sh`
One-time setup script:
1. Validates Docker and Docker Compose
2. Checks base images exist
3. Creates required networks
4. Builds services if needed
5. Verifies security constraints

Run once per project:
```bash
./initialize.sh /absolute/path/to/project
```

### `Dockerfile` (optional)
Extend base image for project needs:
```dockerfile
FROM claudecode/devcontainer:latest

# Add project-specific tools (as non-root user)
USER claude
RUN pip install --user project-dependencies

# Maintain security - no sudo, no root
WORKDIR /workspace
```

## Network Architecture

```
Internet
    ↕
[tinyproxy] - claude-external network (bridge)
    ↕ (proxy only)
[devcontainer] - claude-internal network (internal: true)
    ↕ (local only)
[docker] - claude-internal network (internal: true)
```

**Security Enforcement**:
- Internal network blocks direct internet access
- All HTTP(S) traffic must use proxy
- DNS resolution fails without proxy
- No container can bypass isolation

## IDE Integration

### VS Code
1. Open project folder
2. VS Code detects `.devcontainer/devcontainer.json`
3. Prompts to "Reopen in Container"
4. Automatically configures environment

### PyCharm
1. Configure Docker as Python interpreter
2. Use docker-compose service: `devcontainer`
3. Python path: `/usr/local/bin/python`
4. Working directory: `/workspace`

### Claude Code
```bash
# From devcontainer
claude --dangerously-skip-permissions

# Or from host (if Claude CLI installed)
docker exec -it devcontainer claude --dangerously-skip-permissions
```

## Customization

### Adding Tools
Edit `Dockerfile` to add project-specific tools:
```dockerfile
# Always as non-root user
USER claude
RUN npm install -g project-tool
```

### Adding Whitelisted Domains
Edit `whitelist.txt`:
```
newdomain.com
api.newservice.com
```

Then restart proxy:
```bash
docker compose restart tinyproxy
```

### Environment Variables
Add to `.env`:
```bash
MY_API_KEY=secret
DATABASE_URL=postgresql://...
```

Access in container:
```bash
docker exec devcontainer env | grep MY_
```

## Validation

### Test Network Isolation
```bash
# Should fail (no direct internet)
docker exec devcontainer sh -c 'unset http_proxy https_proxy && curl google.com'

# Should work (via proxy, if whitelisted)
docker exec devcontainer curl https://github.com
```

### Check User Permissions
```bash
# Should show 'claude' user, no sudo
docker exec devcontainer whoami
docker exec devcontainer sudo ls  # Should fail
```

### Verify Proxy Configuration
```bash
# Check environment
docker exec devcontainer env | grep -i proxy

# Test proxy filtering
docker exec devcontainer curl https://whitelisted.com  # OK
docker exec devcontainer curl https://blocked.com      # Denied
```

## Troubleshooting

### Container Won't Start
- Check Docker daemon: `docker ps`
- Verify networks: `docker network ls | grep claude`
- Check logs: `docker compose logs`

### Can't Access External Sites
- Add to `whitelist.txt`
- Restart proxy: `docker compose restart tinyproxy`
- Check proxy logs: `docker logs tinyproxy`

### IDE Can't Connect
- Ensure container running: `docker ps`
- Check service name matches
- Verify Docker socket mounted

### Permission Errors
- Never use sudo in containers
- Check file ownership: should be claude:dev
- Use `chown claude:dev` if needed

## Security Checklist

✅ **Required**:
- [ ] Network internal: `internal: true`
- [ ] User non-root: `claude` (UID 1001)
- [ ] Proxy configured: Port 8888
- [ ] Filter enabled: `FilterDefaultDeny Yes`
- [ ] No sudo access: Commands fail
- [ ] No SSH server: Not installed
- [ ] No passwords: No authentication

❌ **Never**:
- [ ] Change network to external
- [ ] Add sudo or root access
- [ ] Disable proxy filtering
- [ ] Expose container ports
- [ ] Add authentication
- [ ] Install SSH servers

Remember: Security model depends on proper configuration. When extending, maintain all security constraints.