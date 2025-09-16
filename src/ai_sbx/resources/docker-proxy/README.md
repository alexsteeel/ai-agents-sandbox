# Docker Registry Proxy

A transparent caching proxy for Docker images that replaces direct host Docker cache mounts.

## Overview

This setup uses [docker-registry-proxy](https://github.com/rpardini/docker-registry-proxy) to cache Docker images from multiple registries transparently. No need to change image names or use `docker tag` - the proxy intercepts HTTPS requests and caches them automatically.

## Features

- **Transparent caching**: Works with existing image names (no localhost:5000 prefix needed)
- **Multiple registries**: Caches from Docker Hub, gcr.io, quay.io, k8s.io, ghcr.io, and more
- **4GB+ image support**: Efficiently caches large test images
- **Shared cache**: Multiple projects use the same cache
- **Auto-start**: Managed by `ai-sbx init` command

## Quick Start

The proxy is automatically started when you initialize a project:

```bash
ai-sbx init /path/to/project
```

## Architecture

```
Docker Client (in docker-dind)
         ↓
    HTTP_PROXY=ai-sbx-docker-proxy:3128
         ↓
docker-registry-proxy (caching)
         ↓
External Registry (Docker Hub, gcr.io, etc.)
```

## Configuration

### Environment Variables (.env)

```bash
# Max cache size (default 32GB)
CACHE_MAX_SIZE=32g

# Additional registries to cache (space-separated)
ADDITIONAL_REGISTRIES=my.registry.com artifactory.company.com

# Authentication for private registries
AUTH_REGISTRIES="my.registry.com:user:pass"

# Allow push operations (default false)
ALLOW_PUSH=false
```

### Default Cached Registries

- docker.io (Docker Hub)
- gcr.io (Google Container Registry)
- quay.io (Red Hat Quay)
- registry.k8s.io (Kubernetes)
- ghcr.io (GitHub Container Registry)

## How It Works

1. **Proxy Interception**: Docker daemon configured with HTTP(S)_PROXY
2. **CA Certificate**: Custom CA installed in docker-dind for HTTPS interception
3. **Transparent Cache**: Proxy caches layers and manifests
4. **Cache Reuse**: Subsequent pulls use cached data

## Testing

### Verify Proxy is Running

```bash
docker ps | grep ai-sbx-docker-proxy
```

### Test Image Pull

```bash
# From within docker-dind
docker exec ai-agents-sandbox-docker-1 docker pull busybox:latest
```

### Check Cache Hits

```bash
# View proxy logs
docker logs ai-sbx-docker-proxy | grep HIT
```

### Monitor Cache Size

```bash
docker exec ai-sbx-docker-proxy du -sh /docker_mirror_cache/
```

## Volumes

- `ai-sbx-proxy-cache`: Stores cached image layers
- `ai-sbx-proxy-certs`: Contains CA certificates for HTTPS interception

## Networks

- `ai-sbx-proxy-external`: Access to internet
- `ai-sbx-proxy-internal`: Access from docker services

## Troubleshooting

### Connection Refused

If docker can't connect to proxy:
1. Check proxy is running: `docker ps | grep proxy`
2. Verify network connectivity: `docker network ls | grep ai-sbx`
3. Check override file is included in docker-compose.yaml

### Certificate Errors

If you see x509 certificate errors:
1. Verify CA cert is mounted: Check `override.docker-proxy.yaml`
2. Rebuild docker-dind image if needed
3. Verify cert installation in container logs

### Cache Not Working

To verify caching:
1. Pull an image twice
2. Check logs for HIT/MISS: `docker logs ai-sbx-docker-proxy | grep busybox`
3. HIT means cache is working

## Comparison with Previous Solution

| Aspect | Host Mount | Registry Proxy |
|--------|------------|----------------|
| Setup | Complex permissions | Automatic |
| Multi-user | Difficult | Easy |
| Transparency | Full | Full |
| Cache sharing | Host-dependent | Container-based |
| Large images | Direct access | Cached |
| Security | Host exposure | Isolated |

## Security

- Proxy runs in isolated container
- CA certificates are container-specific
- No host filesystem exposure
- Network isolation maintained

## Upstream Proxy Support

For environments requiring registry restrictions:

### Option 1: Direct Upstream Proxy
```bash
# Edit .env
UPSTREAM_PROXY=http://corp-proxy.company.com:8080
```

### Option 2: Use Tinyproxy for Filtering
```bash
# Edit .env
REGISTRY_WHITELIST=registry.company.com,docker.io

# Start with registry filter profile
docker compose --profile registry-filter up -d

# Set proxy URL
UPSTREAM_PROXY=http://tinyproxy-registry:8888
```

This ensures docker-registry-proxy can only access whitelisted registries.

## Maintenance

### Clear Cache

```bash
docker volume rm ai-sbx-proxy-cache
docker compose -f resources/docker-proxy/docker-compose.yaml up -d
```

### Update Proxy

```bash
docker compose -f resources/docker-proxy/docker-compose.yaml pull
docker compose -f resources/docker-proxy/docker-compose.yaml up -d
```

### View Statistics

```bash
# Cache usage
docker exec ai-sbx-docker-proxy df -h /docker_mirror_cache

# Request stats
docker logs ai-sbx-docker-proxy | jq -r '.upstream_cache_status' | sort | uniq -c
```