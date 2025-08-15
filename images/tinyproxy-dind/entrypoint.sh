#!/bin/sh
set -e

touch /etc/tinyproxy/filter

# Add user whitelist from environment variable if provided
if [ -n "$USER_WHITELIST_DOMAINS" ]; then
    echo "$USER_WHITELIST_DOMAINS" | tr ',' '\n' | tr ' ' '\n' | while read -r domain; do
        if [ -n "$domain" ]; then
            echo "$domain" >> /etc/tinyproxy/filter
        fi
    done
fi

echo "Starting tinyproxy-dind with direct access (no upstream proxy)"
echo "Allowed domains:"
cat /etc/tinyproxy/filter

exec tinyproxy -d -c /etc/tinyproxy/tinyproxy.conf