#!/bin/bash
set -euo pipefail

# Unified build script for both devcontainer and tinyproxy images

echo "========================================"
echo "    Building Docker Images"
echo "========================================"
echo ""

# Function to build an image
build_image() {
    local dockerfile_dir="$1"
    local image_name="$2"
    local image_tag="${3:-latest}"
    
    echo "Building ${image_name}:${image_tag} from ${dockerfile_dir}/Dockerfile..."
    echo "----------------------------------------"
    
    if [[ ! -f "${dockerfile_dir}/Dockerfile" ]]; then
        echo "Error: Dockerfile not found in ${dockerfile_dir}"
        return 1
    fi
    
    # Use parent directory as context, specify Dockerfile path
    docker build -t "${image_name}:${image_tag}" -f "${dockerfile_dir}/Dockerfile" .
    
    if [[ $? -eq 0 ]]; then
        echo "✓ Successfully built ${image_name}:${image_tag}"
    else
        echo "✗ Failed to build ${image_name}:${image_tag}"
        return 1
    fi
    echo ""
}

# Parse command line arguments
BUILD_DEVCONTAINER=false
BUILD_TINYPROXY=false

if [[ $# -eq 0 ]]; then
    # No arguments - build both
    BUILD_DEVCONTAINER=true
    BUILD_TINYPROXY=true
else
    for arg in "$@"; do
        case $arg in
            devcontainer)
                BUILD_DEVCONTAINER=true
                ;;
            tinyproxy)
                BUILD_TINYPROXY=true
                ;;
            all)
                BUILD_DEVCONTAINER=true
                BUILD_TINYPROXY=true
                ;;
            *)
                echo "Usage: $0 [devcontainer|tinyproxy|all]"
                echo "  devcontainer - Build devcontainer base image"
                echo "  tinyproxy    - Build tinyproxy with whitelist image"
                echo "  all          - Build both images (default)"
                exit 1
                ;;
        esac
    done
fi

# Build devcontainer base image
if [[ "$BUILD_DEVCONTAINER" == true ]]; then
    echo "=== Building DevContainer Base Image ==="
    build_image "devcontainer_base" "claudecode/devcontainer" "latest"
fi

# Build tinyproxy image
if [[ "$BUILD_TINYPROXY" == true ]]; then
    echo "=== Building Tinyproxy Whitelist Image ==="
    build_image "tinyproxy_extended" "tinyproxy-whitelist" "latest"
fi

echo "========================================"
echo "    Build Summary"
echo "========================================"

if [[ "$BUILD_DEVCONTAINER" == true ]]; then
    echo "✓ DevContainer: claudecode/devcontainer:latest"
fi

if [[ "$BUILD_TINYPROXY" == true ]]; then
    echo "✓ Tinyproxy: tinyproxy-whitelist:latest"
fi