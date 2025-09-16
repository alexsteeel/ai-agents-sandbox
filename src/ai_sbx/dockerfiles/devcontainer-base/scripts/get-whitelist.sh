#!/bin/bash
set -uo pipefail
IFS=$'\n\t'

# Utility script to get whitelisted domains from configuration files
# Returns unique sorted list of domains

# Function to read domains from a file
read_domains_from_file() {
    local file="$1"
    if [[ -f "$file" ]]; then
        # Skip comments and empty lines, extract domains
        grep -v '^#' "$file" 2>/dev/null | grep -v '^$' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'
    fi
}

# Function to get all whitelisted domains
get_all_whitelisted_domains() {
    local default_domains_file="/usr/local/etc/default-whitelist.txt"

    # Combine all domain sources
    {
        # Default domains (now in devcontainer image)
        read_domains_from_file "$default_domains_file"
        
        # User-defined domains from environment variable
        if [[ -n "${USER_WHITELIST_DOMAINS:-}" ]]; then
            echo "$USER_WHITELIST_DOMAINS" | tr ',' '\n' | tr ' ' '\n' | grep -v '^$'
        fi
    } | sort -u
}

# Function to check if a domain is whitelisted
is_domain_whitelisted() {
    local domain="$1"
    local whitelisted_domains
    whitelisted_domains=$(get_all_whitelisted_domains)
    
    echo "$whitelisted_domains" | grep -q "^${domain}$"
}

# Main execution
case "${1:-list}" in
    list)
        # List all whitelisted domains
        get_all_whitelisted_domains
        ;;
    check)
        # Check if a specific domain is whitelisted
        if [[ -z "${2:-}" ]]; then
            echo "Usage: $0 check <domain>"
            exit 1
        fi
        if is_domain_whitelisted "$2"; then
            echo "Domain '$2' is whitelisted"
            exit 0
        else
            echo "Domain '$2' is not whitelisted"
            exit 1
        fi
        ;;
    count)
        # Count total whitelisted domains
        get_all_whitelisted_domains | wc -l
        ;;
    *)
        echo "Usage: $0 {list|check <domain>|count}"
        exit 1
        ;;
esac