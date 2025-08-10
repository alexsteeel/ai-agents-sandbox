#!/bin/bash
set -euo pipefail
IFS=$'\n\t'

# Network connectivity tests for devcontainer
# Tests proxy connectivity and domain filtering

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test result tracking
TESTS_PASSED=0
TESTS_FAILED=0

# Function to test domain access
test_domain_access() {
    local domain="$1"
    local expected="$2"  # "whitelisted" or "blocked"
    local result
    
    # Test with curl using HTTP HEAD request through proxy
    local http_code
    # curl should use HTTP_PROXY/HTTPS_PROXY from environment  
    if [[ -n "${HTTP_PROXY:-}" ]]; then
        # Get HTTP status code directly from curl
        http_code=$(curl --max-time 5 -ILs -o /dev/null -w '%{http_code}' "$domain" 2>/dev/null || echo "000")
        
        # If we get 000 (or 000000), check if it's a 403 Filtered response from proxy
        if [[ "$http_code" =~ ^0+$ ]]; then
            if curl --max-time 5 -Is "$domain" 2>&1 | grep -q "403 Filtered"; then
                http_code="403"
            fi
        fi
    else
        http_code="000"
    fi
    
    # Determine if domain is accessible
    # 000 = connection failed/timeout (usually means blocked)
    # 403 = could be either tinyproxy filter OR server access denied
    # 200-499 (except 403 from filter) = connection allowed
    # 502 = bad gateway (usually proxy error)
    
    # Handle both "000" and "000000" (sometimes curl returns 6 zeros)
    if [[ "$http_code" =~ ^0+$ || "$http_code" == "502" ]]; then
        result="blocked"
    elif [[ "$http_code" == "403" ]]; then
        # Check if it's tinyproxy's filter message
        if curl --max-time 5 -s "$domain" 2>&1 | grep -q "The request you made has been filtered"; then
            result="blocked"
        else
            # It's a 403 from the actual server (like frameworks.jetbrains.com), so connection was allowed
            result="whitelisted"
        fi
    else
        # Any other HTTP code means connection was successful
        result="whitelisted"
    fi
    
    # Check if result matches expectation
    if [[ "$result" == "$expected" ]]; then
        echo -e "${GREEN}✓${NC} $domain: $expected (HTTP $http_code)"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $domain: expected $expected, got $result (HTTP $http_code)"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Function to verify proxy connectivity
check_proxy_connectivity() {
    echo "=== Proxy Connectivity Test ==="
    
    # Check if proxy environment variables are set
    if [[ -z "${HTTP_PROXY:-}" ]] || [[ -z "${HTTPS_PROXY:-}" ]]; then
        echo -e "${RED}✗${NC} Proxy environment variables not set"
        ((TESTS_FAILED++))
        return 1
    fi
    
    echo -e "${GREEN}✓${NC} HTTP_PROXY=${HTTP_PROXY}"
    echo -e "${GREEN}✓${NC} HTTPS_PROXY=${HTTPS_PROXY}"
    ((TESTS_PASSED+=2))
    
    # Test direct connection (should fail due to internal network)
    echo ""
    echo "Testing network isolation (direct connection should fail):"
    # Run in subshell to avoid affecting parent environment
    if (unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY && curl --max-time 3 -s https://github.com 2>&1 | grep -q "Could not resolve host"); then
        echo -e "${GREEN}✓${NC} Network isolation working (direct connection blocked)"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Network isolation may not be working properly"
    fi
    
    return 0
}

# Function to get domains to test (uses get-whitelist.sh)
get_whitelisted_domains() {
    # Use the get-whitelist.sh script to get domains
    local script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    "${script_dir}/get-whitelist.sh" list
}

# Function to test whitelisted domains
test_whitelisted_domains() {
    echo ""
    echo "=== Testing Whitelisted Domains ==="
    
    # Get all whitelisted domains
    local whitelisted_domains
    readarray -t whitelisted_domains < <(get_whitelisted_domains)
    
    local total_domains=${#whitelisted_domains[@]}
    echo "Found $total_domains whitelisted domains total"
    
    # Test a subset of domains (max 20 for brevity)
    local max_test=20
    local test_count=$((total_domains < max_test ? total_domains : max_test))
    
    echo "Testing $test_count whitelisted domains:"
    for ((i=0; i<test_count; i++)); do
        test_domain_access "${whitelisted_domains[$i]}" "whitelisted" || true
    done
    
    if [[ $total_domains -gt $max_test ]]; then
        echo "... and $((total_domains - max_test)) more domains configured"
    fi
}

# Function to test blocked domains
test_blocked_domains() {
    echo ""
    echo "=== Testing Blocked Domains ==="
    
    # Domains that should be blocked
    local BLOCKED_DOMAINS=(
        "google.com"
        "facebook.com"
        "twitter.com"
        "youtube.com"
        "amazon.com"
        "netflix.com"
        "reddit.com"
        "wikipedia.org"
    )
    
    echo "Testing domain filtering (these should be blocked):"
    for domain in "${BLOCKED_DOMAINS[@]:0:5}"; do
        test_domain_access "$domain" "blocked" || true
    done
}

# Function to test DNS resolution
test_dns_resolution() {
    echo ""
    echo "=== DNS Resolution Test ==="
    
    # DNS resolution doesn't work directly in isolated network
    # But we can test if domains resolve through the proxy
    if curl --max-time 3 -s -o /dev/null -w "%{http_code}" https://github.com >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Domain resolution working through proxy"
        ((TESTS_PASSED++))
    else
        echo -e "${YELLOW}⚠${NC} Domain resolution may have issues"
    fi
    
    # Note about direct DNS
    echo -e "${YELLOW}ℹ${NC} Direct DNS (nslookup) not available in isolated network (expected)"
}

# Main test execution
main() {
    echo "========================================"
    echo "    Network Connectivity Tests"
    echo "========================================"
    echo "Date: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
    echo ""
    
    # Run tests
    check_proxy_connectivity
    test_whitelisted_domains
    test_blocked_domains
    test_dns_resolution
    
    # Summary
    echo ""
    echo "========================================"
    echo "Test Summary:"
    echo -e "${GREEN}Passed:${NC} $TESTS_PASSED"
    echo -e "${RED}Failed:${NC} $TESTS_FAILED"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}All network tests passed!${NC}"
        exit 0
    else
        echo -e "${YELLOW}Some tests failed. Check proxy configuration.${NC}"
        exit 1
    fi
}

# Run tests
main "$@"