# Architecture

## System Overview

AI Agents Sandbox provides secure, isolated development environments for AI-assisted coding with strict network controls and security boundaries.

![Architecture Diagram](architecture.png)

## Key Components

### Host PC
- Runs PyCharm IDE or VS Code
- Manages git worktrees for task isolation
- Connects to containers via Docker API

### Project Worktree Network (Isolated)
The main development environment with **no direct internet access**:

#### Devcontainer
Primary development container where all AI agents work together:
- **PyCharm IDE Backend** - Remote development server
- **Claude Code** - AI coding assistant
- **Codex CLI** - Code review and analysis
- **Docker CLI** - Container management

All agents share the same sandbox environment for seamless collaboration.

#### Docker-in-Docker
Provides Docker daemon functionality inside the isolated environment:
- Runs as a separate service
- Allows building and running containers
- Isolated from host Docker daemon

### Network Architecture

#### Internal Network (Isolated)
- **Type**: Bridge network with `internal: true`
- **Purpose**: Complete isolation from internet
- **Access**: No direct external connectivity
- Used by devcontainer and docker-dind services

#### External Network  
- **Type**: Bridge network with internet access
- **Purpose**: Controlled egress through proxy
- Used by tinyproxy and docker-registry-proxy

### Proxy Layer

#### Tinyproxy
- **Port**: 8888
- **Function**: HTTP/HTTPS proxy with whitelist filtering
- **Policy**: Default deny - only whitelisted URLs allowed
- **Configuration**: Dynamic whitelist from environment variables

#### Docker Registry Proxy
- **Port**: 3128
- **Function**: Caches Docker images from registries
- **Isolation**: Separate from main proxy
- **Benefits**: Faster builds, reduced bandwidth

### Service Layer (Optional)

Additional services can be added as needed:

#### Interpreter Container
Python development container for isolated execution

#### Databases & Storage
- **PostgreSQL** - Relational database
- **MinIO** - S3-compatible object storage  
- **Redis** - Cache and message broker

### Security Model

1. **Network Isolation**
   - Internal network blocks all direct internet access
   - All traffic must go through proxy

2. **Proxy Filtering**
   - Whitelist-only access to approved domains
   - Separate proxy for Docker registry access

3. **Container Security**
   - Non-root user (claude, UID 1001)
   - No sudo access
   - No SSH servers
   - Minimal attack surface

4. **Workspace Isolation**
   - Each task runs in separate git worktree
   - Independent container instances per worktree
   - No cross-task contamination

## Data Flow

1. **Development Flow**
   ```
   Host IDE → Docker API → Devcontainer → Code/Tools
   ```

2. **Internet Access Flow**
   ```
   Devcontainer → Tinyproxy → [Whitelist Check] → Internet
   ```

3. **Docker Image Pull Flow**
   ```
   Docker-in-Docker → Docker Registry Proxy → Registry → Internet
   ```

## Configuration

### Proxy Configuration
- Whitelist domains via `USER_WHITELIST_DOMAINS` environment variable
- Upstream proxy support via `UPSTREAM_PROXY` 
- Registry configuration in `resources/docker-proxy/.env`

### Network Configuration
- Networks defined in `docker-compose.yaml`
- Internal network must have `internal: true`
- External network for proxy services only

### Service Configuration
- Main services in base docker-compose
- Optional services via compose overlays
- Project-specific overrides in `override.user.yaml`

## Benefits

1. **Security**: Complete network isolation with controlled egress
2. **Flexibility**: Add services as needed without compromising security
3. **Performance**: Local Docker registry cache speeds up builds
4. **Isolation**: Each task completely isolated from others
5. **Collaboration**: All AI agents work in same environment