# tinyproxy_extended/CLAUDE.md

This directory contains the custom tinyproxy Docker image for secure proxy filtering.

## Purpose

Extends the standard tinyproxy image with:
- Dynamic configuration via environment variables
- Automatic upstream proxy support
- Whitelist merging from multiple sources
- Default-deny filtering policy

## Build Process

Built automatically by `build.sh` script:
```bash
# From project root
./build.sh  # Builds claudecode/tinyproxy:latest
```

## Components

### `Dockerfile`
- Based on `tinyproxy/tinyproxy:latest`
- Adds custom entrypoint for dynamic configuration
- Includes utilities for whitelist management

### `entrypoint.sh`
Dynamic configuration script that:
1. **Merges whitelists** from multiple sources:
   - `/default-whitelist.txt` (built-in defaults)
   - `/common-whitelist.txt` (common settings)
   - `/custom-whitelist.txt` (project-specific)

2. **Configures upstream proxy** (if environment variables set):
   - HTTP proxy: Uses `UPSTREAM_HTTP=host:port` format
   - SOCKS5 proxy: Uses `UPSTREAM_SOCKS5=host:port` format
   - Bypass domains: Uses `NO_UPSTREAM` for domains that skip upstream
   - Only one proxy type (HTTP or SOCKS5) can be active

3. **Generates tinyproxy.conf** with:
   - Port 8888 binding
   - Default-deny policy (`FilterDefaultDeny Yes`)
   - Merged filter file
   - Logging configuration
   - No upstream directives for bypass domains

### `tinyproxy.conf`
Template configuration with:
- **Security settings**: Default deny all domains
- **Performance**: Optimized for development use
- **Logging**: Comprehensive logging for debugging
- **No authentication**: Relies on network isolation

## Environment Variables

Configured via `.env` file:

```bash
# Optional: External HTTP proxy (choose one)
UPSTREAM_HTTP=proxy.example.com:3128

# OR: External SOCKS5 proxy
UPSTREAM_SOCKS5=socks.example.com:1080

# Optional: Domains that bypass upstream proxy
# Can be space or comma separated
NO_UPSTREAM="github.com gitlab.com,bitbucket.org"
```

### NO_UPSTREAM Feature
When an upstream proxy is configured, you can specify domains that should connect directly through tinyproxy without going through the upstream:
- Useful for local/internal services
- Supports multiple domains (space or comma separated)
- Only applies when `UPSTREAM_HTTP` or `UPSTREAM_SOCKS5` is set
- Each domain gets a `no upstream "domain"` directive in the config

## Whitelist Management

### Adding Domains
Edit `.devcontainer/whitelist.txt` (one domain per line):
```
example.com
api.example.com
*.example.org
```

### Default Domains
Includes common development domains:
- GitHub and Git hosting
- Package registries (npm, pip, cargo)
- Documentation sites
- CI/CD services

### Verification
Test whitelist filtering:
```bash
# Should work (whitelisted)
docker exec devcontainer curl https://github.com

# Should fail (not whitelisted)
docker exec devcontainer curl https://unauthorized.com
```

## Security Model

**Network Isolation**:
- Proxy is the ONLY gateway to internet
- Containers on internal network cannot bypass
- DNS resolution blocked without proxy

**Filter Policy**:
- Default deny all domains
- Only explicit whitelist allowed
- No regex patterns (exact domain match)
- Subdomains must be explicitly listed

## Troubleshooting

### Check Proxy Logs
```bash
docker logs tinyproxy
```

### Verify Configuration
```bash
docker exec tinyproxy cat /etc/tinyproxy/tinyproxy.conf
docker exec tinyproxy cat /etc/tinyproxy/filter
```

### Test Connectivity
```bash
# From devcontainer
curl -I https://github.com  # Should work
curl -I https://google.com  # Should fail (unless whitelisted)
```

### Common Issues

**"Access denied" for legitimate sites**:
- Add domain to `.devcontainer/whitelist.txt`
- Restart tinyproxy: `docker compose restart tinyproxy`

**Upstream proxy not working**:
- Verify `UPSTREAM_HTTP` or `UPSTREAM_SOCKS5` format in `.env`
- Check upstream proxy accessibility
- For SOCKS5: Ensure format is `host:port` (e.g., `socks.example.com:1080`)
- For HTTP: Ensure format is `host:port` (e.g., `proxy.example.com:3128`)

**Bypass domains not working**:
- Verify `NO_UPSTREAM` is set correctly in `.env`
- Ensure upstream proxy is configured (bypass only works with upstream)
- Check logs for "no upstream" directives being added

## Important Notes

- **Never disable FilterDefaultDeny**: Core security control
- **Whitelist carefully**: Each domain increases attack surface
- **Monitor logs**: Review access patterns regularly
- **No authentication**: Relies entirely on network isolation