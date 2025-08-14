# Templates Directory

This directory contains Docker Compose templates that serve as the foundation for devcontainer implementations.

## docker-compose.base.yaml

The base template that projects should extend from. Key architectural decisions:

### Network Isolation

**CRITICAL: Strict proxy separation is enforced**
- `devcontainer` service uses ONLY `tinyproxy-devcontainer:8888`
- `docker` service uses ONLY `tinyproxy-dind:8888`
- No shared proxy configuration between services
- Each service has hardcoded proxy endpoints to prevent misconfiguration

### Service Configuration

**devcontainer service:**
- Uses `x-devcontainer-proxy-env` anchor for proxy settings
- Proxy hardcoded to `http://tinyproxy-devcontainer:8888`
- Includes `docker` in NO_PROXY to allow Docker CLI communication
- Depends only on its designated proxy service

**docker service:**
- Proxy settings hardcoded to `http://tinyproxy-dind:8888`
- No variable substitution allowed - prevents accidental proxy mixing
- Isolated on claude-internal network
- Depends only on tinyproxy-dind

### Usage in Projects

Projects should extend this base template:
```yaml
extends:
  file: ../templates/docker-compose.base.yaml
  service: devcontainer
```

Never modify proxy configurations in extending files - the isolation is critical for security.

## Security Enforcement

The template enforces:
1. Network isolation via `internal: true` networks
2. Proxy-only internet access
3. Service-specific proxy paths with no cross-contamination
4. Non-root user execution
5. No direct port exposure

## Important Notes

- NEVER use shared proxy environment variables
- NEVER allow devcontainer to use tinyproxy-dind
- NEVER allow docker service to use tinyproxy-devcontainer
- Always maintain strict service-to-proxy mapping as defined in architecture