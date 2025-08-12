#!/bin/sh
set -e

# Default whitelist for container registries
DEFAULT_WHITELIST="
# Docker Hub
docker.io
registry-1.docker.io
index.docker.io
auth.docker.io
production.cloudflare.docker.com
download.docker.com

# Docker CDN and storage (regex patterns)
\.r2\.cloudflarestorage\.com
\.cloudfront\.net
\.amazonaws\.com

# GitHub Container Registry
ghcr.io
pkg-containers.githubusercontent.com
github.com
raw.githubusercontent.com

# Google Container Registry
gcr.io
storage.googleapis.com
k8s.gcr.io

# Quay Registry
quay.io
cdn.quay.io
cdn01.quay.io
cdn02.quay.io
cdn03.quay.io

# Microsoft Container Registry
mcr.microsoft.com

# Red Hat Registry
registry.redhat.io
registry.access.redhat.com

# Essential package registries
registry.npmjs.org
pypi.org
files.pythonhosted.org
"

# Clear and recreate filter file
> /etc/tinyproxy/filter

# Add default whitelist
echo "$DEFAULT_WHITELIST" | while read -r domain; do
    # Skip empty lines and comments
    if [ -n "$domain" ] && [ "${domain#\#}" = "$domain" ]; then
        echo "$domain" >> /etc/tinyproxy/filter
    fi
done

# Add user-provided whitelist if it exists
if [ -f /etc/tinyproxy/user-whitelist.txt ]; then
    cat /etc/tinyproxy/user-whitelist.txt | while read -r domain; do
        # Skip empty lines and comments
        if [ -n "$domain" ] && [ "${domain#\#}" = "$domain" ]; then
            echo "$domain" >> /etc/tinyproxy/filter
        fi
    done
fi

echo "Starting tinyproxy-dind with direct access (no upstream proxy)"
echo "Allowed domains:"
cat /etc/tinyproxy/filter

# Start tinyproxy in foreground
exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf