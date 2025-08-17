#!/bin/bash
set -euo pipefail

# Unified build script for all Docker images
# This script builds all images required for the AI Agents Sandbox system

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use IMAGE_TAG from environment if set, otherwise default to "latest"
DEFAULT_TAG="${IMAGE_TAG:-latest}"

# Image names
IMAGE_DEVCONTAINER="ai-agents-sandbox/devcontainer"
IMAGE_TINYPROXY_BASE="ai-agents-sandbox/tinyproxy-base"
IMAGE_TINYPROXY="ai-agents-sandbox/tinyproxy"
IMAGE_DOCKER_DIND="ai-agents-sandbox/docker-dind"
IMAGE_DOTNET="ai-agents-sandbox/devcontainer-dotnet"
IMAGE_GOLANG="ai-agents-sandbox/devcontainer-golang"

# Color output for better readability
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to build an image with error handling
build_image() {
    local dockerfile_dir="$1"
    local image_name="$2"
    local image_tag="${3:-$DEFAULT_TAG}"
    
    print_status "Building ${image_name}:${image_tag} from ${dockerfile_dir}..."
    
    if [[ ! -f "${dockerfile_dir}/Dockerfile" ]]; then
        print_error "Dockerfile not found in ${dockerfile_dir}"
        return 1
    fi
    
    # Build with proper context (parent directory) and pass IMAGE_TAG as build arg
    if docker build --build-arg IMAGE_TAG="${image_tag}" -t "${image_name}:${image_tag}" -f "${dockerfile_dir}/Dockerfile" .. 2>&1 | tee /tmp/docker_build_$$.log; then
        print_status "✓ Successfully built ${image_name}:${image_tag}"
        rm -f /tmp/docker_build_$$.log
        return 0
    else
        print_error "✗ Failed to build ${image_name}:${image_tag}"
        print_error "Build log saved to /tmp/docker_build_$$.log"
        return 1
    fi
}

# Function to verify image was built
verify_image() {
    local image_name="$1"
    local image_tag="${2:-$DEFAULT_TAG}"
    
    if docker image inspect "${image_name}:${image_tag}" >/dev/null 2>&1; then
        local size=$(docker image inspect "${image_name}:${image_tag}" --format='{{.Size}}' | numfmt --to=iec-i --suffix=B)
        print_status "Image ${image_name}:${image_tag} verified (size: ${size})"
        return 0
    else
        print_error "Image ${image_name}:${image_tag} not found after build"
        return 1
    fi
}

# Parse command line arguments
BUILD_DEVCONTAINER=false
BUILD_TINYPROXY_BASE=false
BUILD_TINYPROXY=false
BUILD_TINYPROXY_DIND=false
BUILD_DOCKER_DIND=false
BUILD_DOTNET=false
BUILD_GOLANG=false
VERIFY_ONLY=false
FORCE_REBUILD=false

if [[ $# -eq 0 ]]; then
    # No arguments - build all
    BUILD_DEVCONTAINER=true
    BUILD_TINYPROXY_BASE=true
    BUILD_TINYPROXY=true
    BUILD_TINYPROXY_DIND=true
    BUILD_DOTNET=true
    BUILD_GOLANG=true
else
    for arg in "$@"; do
        case $arg in
            devcontainer)
                BUILD_DEVCONTAINER=true
                ;;
            tinyproxy-base)
                BUILD_TINYPROXY_BASE=true
                ;;
            tinyproxy)
                BUILD_TINYPROXY=true
                ;;
            tinyproxy-dind)
                BUILD_TINYPROXY_DIND=true
                ;;
            docker-dind)
                BUILD_DOCKER_DIND=true
                ;;
            dotnet)
                BUILD_DOTNET=true
                ;;
            golang|go)
                BUILD_GOLANG=true
                ;;
            all)
                BUILD_DEVCONTAINER=true
                BUILD_TINYPROXY_BASE=true
                BUILD_TINYPROXY=true
                BUILD_TINYPROXY_DIND=true
                BUILD_DOCKER_DIND=true
                BUILD_DOTNET=true
                BUILD_GOLANG=true
                ;;
            --verify)
                VERIFY_ONLY=true
                BUILD_DEVCONTAINER=true
                BUILD_TINYPROXY_BASE=true
                BUILD_TINYPROXY=true
                BUILD_TINYPROXY_DIND=true
                BUILD_DOCKER_DIND=true
                BUILD_DOTNET=true
                BUILD_GOLANG=true
                ;;
            --force)
                FORCE_REBUILD=true
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS] [IMAGES]"
                echo ""
                echo "IMAGES:"
                echo "  devcontainer   - Build devcontainer base image"
                echo "  tinyproxy-base - Build tinyproxy base image"
                echo "  tinyproxy      - Build tinyproxy with whitelist image"
                echo "  tinyproxy-dind - Build tinyproxy for Docker-in-Docker"
                echo "  docker-dind    - Build Docker-in-Docker with registry support"
                echo "  dotnet         - Build .NET 9 devcontainer image"
                echo "  golang, go     - Build Go devcontainer image"
                echo "  all            - Build all images (default)"
                echo ""
                echo "OPTIONS:"
                echo "  --verify       - Only verify that images exist"
                echo "  --force        - Force rebuild even if images exist"
                echo "  --help, -h     - Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                    # Build all images"
                echo "  $0 devcontainer       # Build only devcontainer"
                echo "  $0 --verify           # Verify all images exist"
                echo "  $0 --force all        # Force rebuild all images"
                exit 0
                ;;
            *)
                print_error "Unknown argument: $arg"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
fi

echo "========================================"
echo "    AI Agents Sandbox Image Builder"
echo "========================================"
echo "    Image Tag: $DEFAULT_TAG"
echo "========================================"
echo ""

# Track build results
BUILD_FAILED=false

# Verify only mode
if [[ "$VERIFY_ONLY" == true ]]; then
    print_status "Verifying images..."
    
    if [[ "$BUILD_DEVCONTAINER" == true ]]; then
        verify_image "$IMAGE_DEVCONTAINER" "$DEFAULT_TAG" || BUILD_FAILED=true
    fi
    
    if [[ "$BUILD_TINYPROXY_BASE" == true ]]; then
        verify_image "$IMAGE_TINYPROXY_BASE" "$DEFAULT_TAG" || BUILD_FAILED=true
    fi
    
    if [[ "$BUILD_TINYPROXY" == true ]]; then
        verify_image "$IMAGE_TINYPROXY" "$DEFAULT_TAG" || BUILD_FAILED=true
    fi
    
    if [[ "$BUILD_TINYPROXY_DIND" == true ]]; then
        verify_image "$IMAGE_TINYPROXY_DIND" "$DEFAULT_TAG" || BUILD_FAILED=true
    fi
    
    if [[ "$BUILD_DOCKER_DIND" == true ]]; then
        verify_image "$IMAGE_DOCKER_DIND" "$DEFAULT_TAG" || BUILD_FAILED=true
    fi
    
    if [[ "$BUILD_DOTNET" == true ]]; then
        verify_image "$IMAGE_DOTNET" "$DEFAULT_TAG" || BUILD_FAILED=true
    fi
    
    if [[ "$BUILD_GOLANG" == true ]]; then
        verify_image "$IMAGE_GOLANG" "$DEFAULT_TAG" || BUILD_FAILED=true
    fi
    
    if [[ "$BUILD_FAILED" == true ]]; then
        print_error "Some images are missing. Run without --verify to build them."
        exit 1
    else
        print_status "All required images are present."
        exit 0
    fi
fi

# Check for existing images and skip if not forcing rebuild
check_and_build() {
    local dir="$1"
    local name="$2"
    local tag="${3:-$DEFAULT_TAG}"
    
    if [[ "$FORCE_REBUILD" != true ]] && docker image inspect "${name}:${tag}" >/dev/null 2>&1; then
        print_warning "Image ${name}:${tag} already exists. Use --force to rebuild."
        return 0
    fi
    
    build_image "$dir" "$name" "$tag" || BUILD_FAILED=true
}

# Build devcontainer base image
if [[ "$BUILD_DEVCONTAINER" == true ]]; then
    echo "=== Building DevContainer Base Image ==="
    check_and_build "devcontainer-base" "$IMAGE_DEVCONTAINER" "$DEFAULT_TAG"
    echo ""
fi

# Build tinyproxy base image
if [[ "$BUILD_TINYPROXY_BASE" == true ]]; then
    echo "=== Building Tinyproxy Base Image ==="
    check_and_build "tinyproxy-base" "$IMAGE_TINYPROXY_BASE" "$DEFAULT_TAG"
    echo ""
fi

# Build tinyproxy image
if [[ "$BUILD_TINYPROXY" == true ]]; then
    echo "=== Building Tinyproxy Whitelist Image ==="
    check_and_build "tinyproxy" "$IMAGE_TINYPROXY" "$DEFAULT_TAG"
    echo ""
fi

# Build tinyproxy-registry image
if [[ "$BUILD_TINYPROXY_REGISTRY" == true ]]; then
    echo "=== Building Tinyproxy Registry Image ==="
    check_and_build "tinyproxy-registry" "$IMAGE_TINYPROXY_REGISTRY" "$DEFAULT_TAG"
    echo ""
fi

# Build docker-dind image
if [[ "$BUILD_DOCKER_DIND" == true ]]; then
    echo "=== Building Docker DinD Image ==="
    check_and_build "docker-dind" "$IMAGE_DOCKER_DIND" "$DEFAULT_TAG"
    echo ""
fi

# Build .NET devcontainer image
if [[ "$BUILD_DOTNET" == true ]]; then
    echo "=== Building .NET 9 DevContainer Image ==="
    check_and_build "devcontainer-dotnet" "$IMAGE_DOTNET" "$DEFAULT_TAG"
    echo ""
fi

# Build Go devcontainer image
if [[ "$BUILD_GOLANG" == true ]]; then
    echo "=== Building Go DevContainer Image ==="
    check_and_build "devcontainer-golang" "$IMAGE_GOLANG" "$DEFAULT_TAG"
    echo ""
fi

echo "========================================"
echo "    Build Summary"
echo "========================================"

# Show summary and verify all builds
if [[ "$BUILD_DEVCONTAINER" == true ]]; then
    if verify_image "$IMAGE_DEVCONTAINER" "$DEFAULT_TAG"; then
        echo "✓ DevContainer: ${IMAGE_DEVCONTAINER}:${DEFAULT_TAG}"
    else
        echo "✗ DevContainer: Build failed or image not found"
        BUILD_FAILED=true
    fi
fi

if [[ "$BUILD_TINYPROXY_BASE" == true ]]; then
    if verify_image "$IMAGE_TINYPROXY_BASE" "$DEFAULT_TAG"; then
        echo "✓ Tinyproxy Base: ${IMAGE_TINYPROXY_BASE}:${DEFAULT_TAG}"
    else
        echo "✗ Tinyproxy Base: Build failed or image not found"
        BUILD_FAILED=true
    fi
fi

if [[ "$BUILD_TINYPROXY" == true ]]; then
    if verify_image "$IMAGE_TINYPROXY" "$DEFAULT_TAG"; then
        echo "✓ Tinyproxy: ${IMAGE_TINYPROXY}:${DEFAULT_TAG}"
    else
        echo "✗ Tinyproxy: Build failed or image not found"
        BUILD_FAILED=true
    fi
fi

if [[ "$BUILD_TINYPROXY_REGISTRY" == true ]]; then
    if verify_image "$IMAGE_TINYPROXY_REGISTRY" "$DEFAULT_TAG"; then
        echo "✓ Tinyproxy Registry: ${IMAGE_TINYPROXY_REGISTRY}:${DEFAULT_TAG}"
    else
        echo "✗ Tinyproxy Registry: Build failed or image not found"
        BUILD_FAILED=true
    fi
fi

if [[ "$BUILD_DOCKER_DIND" == true ]]; then
    if verify_image "$IMAGE_DOCKER_DIND" "$DEFAULT_TAG"; then
        echo "✓ Docker DinD: ${IMAGE_DOCKER_DIND}:${DEFAULT_TAG}"
    else
        echo "✗ Docker DinD: Build failed or image not found"
        BUILD_FAILED=true
    fi
fi

if [[ "$BUILD_DOTNET" == true ]]; then
    if verify_image "$IMAGE_DOTNET" "$DEFAULT_TAG"; then
        echo "✓ .NET DevContainer: ${IMAGE_DOTNET}:${DEFAULT_TAG}"
    else
        echo "✗ .NET DevContainer: Build failed or image not found"
        BUILD_FAILED=true
    fi
fi

if [[ "$BUILD_GOLANG" == true ]]; then
    if verify_image "$IMAGE_GOLANG" "$DEFAULT_TAG"; then
        echo "✓ Go DevContainer: ${IMAGE_GOLANG}:${DEFAULT_TAG}"
    else
        echo "✗ Go DevContainer: Build failed or image not found"
        BUILD_FAILED=true
    fi
fi

echo ""

if [[ "$BUILD_FAILED" == true ]]; then
    print_error "Some builds failed. Check the logs above for details."
    exit 1
else
    print_status "All builds completed successfully!"
    exit 0
fi