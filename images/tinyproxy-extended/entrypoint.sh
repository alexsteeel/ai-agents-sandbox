#!/bin/sh
set -e

# Merge default whitelist with user whitelist if provided
echo "Preparing Tinyproxy whitelist filter..."

# Start with default whitelist
cat /etc/tinyproxy/default-whitelist.txt > /tmp/domains.txt 2>/dev/null || true

# Add user whitelist if mounted
if [ -f /etc/tinyproxy/user-whitelist.txt ]; then
    echo "Adding user-defined domains to whitelist..."
    cat /etc/tinyproxy/user-whitelist.txt >> /tmp/domains.txt
fi

# Process domains and create filter file
echo "# Tinyproxy whitelist filter" > /etc/tinyproxy/filter
echo "# Generated at $(date)" >> /etc/tinyproxy/filter
echo "" >> /etc/tinyproxy/filter

# Remove comments and empty lines, sort unique domains
grep -v '^#' /tmp/domains.txt 2>/dev/null | \
    grep -v '^$' | \
    sed 's/^[[:space:]]*//;s/[[:space:]]*$//' | \
    sort -u | \
    while read -r domain; do
        if [ -n "$domain" ]; then
            # Add regex patterns for domain and subdomains
            echo "${domain}" | sed 's/\./\\./g' >> /etc/tinyproxy/filter
            echo "\\.${domain}" | sed 's/\./\\./g' >> /etc/tinyproxy/filter
        fi
    done

echo "Filter prepared with $(grep -c '^[^#]' /etc/tinyproxy/filter) patterns"

# Always use our config with filtering enabled
mv /etc/tinyproxy/tinyproxy.conf /etc/tinyproxy/tinyproxy.conf.original 2>/dev/null || true
cp -f /etc/tinyproxy/tinyproxy.conf.default /etc/tinyproxy/tinyproxy.conf

# Configure upstream proxy if UPSTREAM_PROXY is set
# Format: socks5://host:port or http://host:port
if [ -n "$UPSTREAM_PROXY" ]; then
    # Parse the proxy URL
    if echo "$UPSTREAM_PROXY" | grep -q "^socks5://"; then
        # SOCKS5 proxy
        PROXY_HOST_PORT=$(echo "$UPSTREAM_PROXY" | sed 's|socks5://||')
        echo "Configuring upstream SOCKS5 proxy: $PROXY_HOST_PORT"
        echo "" >> /etc/tinyproxy/tinyproxy.conf
        echo "# Upstream SOCKS5 proxy configuration" >> /etc/tinyproxy/tinyproxy.conf
        echo "upstream socks5 $PROXY_HOST_PORT" >> /etc/tinyproxy/tinyproxy.conf
    elif echo "$UPSTREAM_PROXY" | grep -q "^http://"; then
        # HTTP proxy
        PROXY_HOST_PORT=$(echo "$UPSTREAM_PROXY" | sed 's|http://||')
        echo "Configuring upstream HTTP proxy: $PROXY_HOST_PORT"
        echo "" >> /etc/tinyproxy/tinyproxy.conf
        echo "# Upstream HTTP proxy configuration" >> /etc/tinyproxy/tinyproxy.conf
        echo "upstream http $PROXY_HOST_PORT" >> /etc/tinyproxy/tinyproxy.conf
    fi
    
    # Process NO_UPSTREAM domains if provided
    if [ -n "$NO_UPSTREAM" ]; then
        echo "Configuring NO_UPSTREAM domains..."
        echo "" >> /etc/tinyproxy/tinyproxy.conf
        echo "# Domains that bypass upstream proxy" >> /etc/tinyproxy/tinyproxy.conf
        
        # Replace commas with spaces and process each domain
        echo "$NO_UPSTREAM" | tr ',' ' ' | tr -s ' ' '\n' | while read -r domain; do
            if [ -n "$domain" ]; then
                # upstream none directive for bypassing upstream proxy
                echo "upstream none \"$domain\"" >> /etc/tinyproxy/tinyproxy.conf
                echo "  - Added upstream none for: $domain"
            fi
        done
    fi
fi

echo "Using config with filtering enabled"
grep -E "^Filter" /etc/tinyproxy/tinyproxy.conf || echo "WARNING: Filter directives not found!"

# Start tinyproxy
echo "Result tinyproxy configuration:"
cat /etc/tinyproxy/tinyproxy.conf
exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf