#!/bin/sh
set -e

# Start with registry-specific whitelist
cp /usr/local/share/tinyproxy/default-registry-whitelist.txt /etc/tinyproxy/filter

# Add user-defined registry domains if provided
if [ -n "$REGISTRY_WHITELIST" ]; then
    echo "Adding user-defined registry domains..."
    # Ensure we start with a newline if the file doesn't end with one
    echo "" >> /etc/tinyproxy/filter
    echo "$REGISTRY_WHITELIST" | tr ',' '\n' | tr ' ' '\n' | while read -r domain; do
        if [ -n "$domain" ]; then
            echo "$domain" >> /etc/tinyproxy/filter
            echo "Added: $domain"
        fi
    done
fi

# Configure upstream proxy if provided
if [ -n "$UPSTREAM_PROXY" ]; then
    echo "Configuring upstream proxy: $UPSTREAM_PROXY"
    
    # Parse the upstream proxy URL
    if echo "$UPSTREAM_PROXY" | grep -q "^socks5://"; then
        # Extract host and port from socks5://host:port
        PROXY_HOST=$(echo "$UPSTREAM_PROXY" | sed 's|socks5://||' | cut -d: -f1)
        PROXY_PORT=$(echo "$UPSTREAM_PROXY" | sed 's|socks5://||' | cut -d: -f2)
        
        # Add SOCKS5 configuration
        echo "upstream socks5 $PROXY_HOST:$PROXY_PORT" >> /etc/tinyproxy/tinyproxy.conf
    elif echo "$UPSTREAM_PROXY" | grep -q "^http://"; then
        # Extract host and port from http://host:port
        PROXY_HOST=$(echo "$UPSTREAM_PROXY" | sed 's|http://||' | cut -d: -f1)
        PROXY_PORT=$(echo "$UPSTREAM_PROXY" | sed 's|http://||' | cut -d: -f2)
        
        # Add HTTP upstream configuration
        echo "upstream http $PROXY_HOST:$PROXY_PORT" >> /etc/tinyproxy/tinyproxy.conf
    fi
    
    # Add no_upstream domains if specified
    if [ -n "$NO_UPSTREAM" ]; then
        echo "$NO_UPSTREAM" | tr ',' '\n' | tr ' ' '\n' | while read -r domain; do
            if [ -n "$domain" ]; then
                echo "no upstream \"$domain\"" >> /etc/tinyproxy/tinyproxy.conf
            fi
        done
    fi
else
    echo "No upstream proxy configured"
fi

echo "Starting tinyproxy-registry for Docker registries only"
echo "Allowed domains:"
cat /etc/tinyproxy/filter | head -20
echo "..."

exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf