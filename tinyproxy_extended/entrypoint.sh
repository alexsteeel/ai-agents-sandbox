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

# Configure upstream proxy if environment variables are set
if [ -n "$UPSTREAM_SOCKS5" ]; then
    # SOCKS5 proxy format: upstream socks5 host:port
    echo "Configuring upstream SOCKS5 proxy: $UPSTREAM_SOCKS5"
    echo "" >> /etc/tinyproxy/tinyproxy.conf
    echo "# Upstream SOCKS5 proxy configuration" >> /etc/tinyproxy/tinyproxy.conf
    echo "upstream socks5 $UPSTREAM_SOCKS5" >> /etc/tinyproxy/tinyproxy.conf
elif [ -n "$UPSTREAM_HTTP" ]; then
    # HTTP proxy format: upstream http host:port
    echo "Configuring upstream HTTP proxy: $UPSTREAM_HTTP"  
    echo "upstream http $UPSTREAM_HTTP" >> /etc/tinyproxy/tinyproxy.conf
fi

echo "Using config with filtering enabled"
grep -E "^Filter" /etc/tinyproxy/tinyproxy.conf || echo "WARNING: Filter directives not found!"

# Start tinyproxy
exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf