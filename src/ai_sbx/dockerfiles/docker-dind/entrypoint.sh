#!/bin/sh
set -e

# Docker-in-Docker entrypoint with proxy support

# Import CA certificate from mounted volume if available
if [ -f /proxy-ca/ca.crt ]; then
    echo "Installing proxy CA certificate..."
    cp /proxy-ca/ca.crt /usr/local/share/ca-certificates/docker-proxy-ca.crt
    update-ca-certificates
fi

# Create daemon.json
mkdir -p /etc/docker
cat > /etc/docker/daemon.json <<EOF
{
  "features": {
    "buildkit": true
  }
}
EOF

echo "Docker daemon configuration:"
cat /etc/docker/daemon.json

# Create systemd directory for Docker service
mkdir -p /etc/systemd/system/docker.service.d

# Configure Docker client to use proxy (will be overridden by environment)
mkdir -p /root/.docker
cat > /root/.docker/config.json <<EOF
{
  "proxies": {
    "default": {
      "httpProxy": "${HTTP_PROXY:-http://ai-sbx-docker-proxy:3128}",
      "httpsProxy": "${HTTPS_PROXY:-http://ai-sbx-docker-proxy:3128}",
      "noProxy": "${NO_PROXY:-localhost,127.0.0.1,docker}"
    }
  }
}
EOF

echo "Docker client proxy configuration:"
cat /root/.docker/config.json

# Proxy environment will be set by docker-compose

exec dockerd-entrypoint.sh "$@"