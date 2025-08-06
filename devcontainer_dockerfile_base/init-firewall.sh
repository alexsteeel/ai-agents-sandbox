#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, and pipeline failures
IFS=$'\n\t'       # Stricter word splitting

# Show help function
show_help() {
    cat << EOF
Usage: $0 [-d|--domains-file <domains_file_path>] [-h|--help]

Initialize firewall with restricted outbound access to allowed domains.

Options:
    -d, --domains-file FILE    Path to file containing additional allowed domains
    -h, --help                Show this help message

Description:
    This script configures iptables to restrict outbound network access to only
    approved domains and IP ranges. It automatically includes GitHub IP ranges
    and common development domains.

Examples:
    $0                                    # Use default domains only
    $0 -d /etc/allowed-domains.txt       # Include additional domains from file
EOF
}

# Parse command line arguments
DOMAINS_FILE=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--domains-file)
            if [[ -z "${2:-}" ]]; then
                echo "Error: --domains-file requires a file path"
                exit 1
            fi
            DOMAINS_FILE="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# 1. Extract Docker DNS info BEFORE any flushing
DOCKER_DNS_RULES=$(iptables-save -t nat | grep "127\.0\.0\.11" || true)

# Flush existing rules and delete existing ipsets
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X
iptables -t mangle -F
iptables -t mangle -X
ipset destroy allowed-domains 2>/dev/null || true

# 2. Selectively restore ONLY internal Docker DNS resolution
if [ -n "$DOCKER_DNS_RULES" ]; then
    echo "Restoring Docker DNS rules..."
    iptables -t nat -N DOCKER_OUTPUT 2>/dev/null || true
    iptables -t nat -N DOCKER_POSTROUTING 2>/dev/null || true
    echo "$DOCKER_DNS_RULES" | xargs -L 1 iptables -t nat
else
    echo "No Docker DNS rules to restore"
fi

# First allow DNS and localhost before any restrictions
# Allow outbound DNS
iptables -A OUTPUT -p udp --dport 53 -j ACCEPT
# Allow inbound DNS responses
iptables -A INPUT -p udp --sport 53 -j ACCEPT
# Allow outbound SSH
iptables -A OUTPUT -p tcp --dport 22 -j ACCEPT
# Allow inbound SSH responses
iptables -A INPUT -p tcp --sport 22 -m state --state ESTABLISHED -j ACCEPT
# Allow localhost
iptables -A INPUT -i lo -j ACCEPT
iptables -A OUTPUT -o lo -j ACCEPT

# Create ipset with CIDR support
ipset create allowed-domains hash:net

# Fetch GitHub meta information and aggregate + add their IP ranges
echo "Fetching GitHub IP ranges..."
gh_ranges=$(curl -s https://api.github.com/meta)
if [ -z "$gh_ranges" ]; then
    echo "ERROR: Failed to fetch GitHub IP ranges"
    exit 1
fi

if ! echo "$gh_ranges" | jq -e '.web and .api and .git' >/dev/null; then
    echo "ERROR: GitHub API response missing required fields"
    exit 1
fi

echo "Processing GitHub IPs..."
while read -r cidr; do
    if [[ ! "$cidr" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[0-9]{1,2}$ ]]; then
        echo "ERROR: Invalid CIDR range from GitHub meta: $cidr"
        exit 1
    fi
    echo "Adding GitHub range $cidr"
    ipset add allowed-domains "$cidr"
done < <(echo "$gh_ranges" | jq -r '(.web + .api + .git)[]' | aggregate -q)

# Function to read domains from a file
read_domains_from_file() {
    local file_path="$1"
    
    if [[ -f "$file_path" ]]; then
        while IFS= read -r domain || [[ -n "$domain" ]]; do
            # Skip empty lines and comments
            [[ -z "$domain" || "$domain" =~ ^[[:space:]]*# ]] && continue
            # Trim whitespace
            domain=$(echo "$domain" | xargs)
            [[ -n "$domain" ]] && echo "$domain"
        done < "$file_path"
    fi
}

# Resolve and add other allowed domains
DEFAULT_DOMAINS=(
    "registry.npmjs.org"
    "api.anthropic.com"
    "sentry.io"
    "statsig.anthropic.com"
    "statsig.com"
    "account.jetbrains.com"
    "plugins.jetbrains.com"
    "www.jetbrains.com"
)

# Read domains from file if provided and file exists, otherwise use default domains
DOMAINS=("${DEFAULT_DOMAINS[@]}")
if [[ -n "$DOMAINS_FILE" && -f "$DOMAINS_FILE" ]]; then
    echo "Using domains from $DOMAINS_FILE"
    readarray -t FILE_DOMAINS < <(read_domains_from_file "$DOMAINS_FILE")
    if [[ ${#FILE_DOMAINS[@]} -gt 0 ]]; then
        echo "Adding ${#FILE_DOMAINS[@]} domains from file to default domains"
        # Add file domains to default domains
        DOMAINS+=("${FILE_DOMAINS[@]}")
    else
        echo "No valid domains found in $DOMAINS_FILE, using only default domains"
    fi
elif [[ -n "$DOMAINS_FILE" ]]; then
    echo "Domains file $DOMAINS_FILE does not exist, ignoring and using only default domains"
else
    echo "No domains file specified, using only default domains list"
fi

DNS_FAILED_DOMAINS=()
for domain in "${DOMAINS[@]}"; do
    echo "Resolving $domain..."
    ips=$(dig +short A "$domain" 2>/dev/null)
    if [ -z "$ips" ]; then
        echo "WARNING: Failed to resolve $domain - DNS lookup returned no results"
        DNS_FAILED_DOMAINS+=("$domain")
        continue
    fi
    
    domain_resolved=false
    while read -r ip; do
        # Skip CNAME responses and other non-IP results
        if [[ ! "$ip" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            echo "Skipping non-IP result for $domain: $ip"
            continue
        fi
        echo "Adding $ip for $domain"
        ipset add allowed-domains "$ip"
        domain_resolved=true
    done < <(echo "$ips")
    
    if [ "$domain_resolved" = false ]; then
        echo "WARNING: No valid IP addresses found for $domain"
        DNS_FAILED_DOMAINS+=("$domain")
    fi
done

# Report DNS resolution failures
if [ ${#DNS_FAILED_DOMAINS[@]} -gt 0 ]; then
    echo "WARNING: Failed to resolve the following domains:"
    for failed_domain in "${DNS_FAILED_DOMAINS[@]}"; do
        echo "  - $failed_domain"
    done
    echo "These domains will not be accessible through the firewall"
fi

# Get host IP from default route
HOST_IP=$(ip route | grep default | awk '{print $3}' | head -n1)
if [[ -z "$HOST_IP" ]]; then
    echo "ERROR: Failed to detect host IP"
    exit 1
fi

# Validate IP format
if [[ ! "$HOST_IP" =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    echo "ERROR: Invalid host IP detected: $HOST_IP"
    exit 1
fi

HOST_NETWORK=$(echo "$HOST_IP" | sed "s/\.[0-9]*$/.0\/24/")
echo "Host network detected as: $HOST_NETWORK"

# Set up remaining iptables rules
iptables -A INPUT -s "$HOST_NETWORK" -j ACCEPT
iptables -A OUTPUT -d "$HOST_NETWORK" -j ACCEPT

# Set default policies to DROP first
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT DROP

# First allow established connections for already approved traffic
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Then allow only specific outbound traffic to allowed domains
iptables -A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT

echo "Firewall configuration complete"
echo "Verifying firewall rules..."

# Test that blocked domains are actually blocked
if curl --connect-timeout 5 https://example.com >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - was able to reach https://example.com"
    exit 1
else
    echo "Firewall verification passed - unable to reach https://example.com as expected"
fi

# Verify access to all allowed domains
VERIFICATION_FAILED=0
for domain in "${DOMAINS[@]}"; do
    echo "Verifying access to $domain..."
    if ! curl --connect-timeout 5 "https://$domain" >/dev/null 2>&1; then
        echo "WARNING: Unable to reach $domain"
        VERIFICATION_FAILED=1
    else
        echo "Firewall verification passed - able to reach $domain as expected"
    fi
done

# Additional specific checks for critical services
echo "Performing additional critical service checks..."

# Verify GitHub API access specifically
if ! curl --connect-timeout 5 https://api.github.com/zen >/dev/null 2>&1; then
    echo "ERROR: Firewall verification failed - unable to reach https://api.github.com"
    exit 1
else
    echo "Critical service verification passed - GitHub API accessible"
fi

if [[ $VERIFICATION_FAILED -eq 1 ]]; then
    echo "WARNING: Some domain verifications failed, but continuing with firewall setup"
else
    echo "All domain verifications passed successfully"
fi