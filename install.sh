#!/bin/bash
set -euo pipefail

# AI Agents Sandbox System Installer
# This is the master installer that sets up everything:
# - Builds all Docker images
# - Installs host scripts system-wide
# - Sets up templates and documentation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Version
VERSION="1.0.0"

# Common Docker image tag for all images
IMAGE_TAG="1.0.0"
export IMAGE_TAG

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo ""
    printf "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
    printf "${BOLD}${BLUE}   AI Agents Sandbox Installer v${VERSION}${NC}\n"
    printf "${BOLD}${BLUE}   Image Tag: ${IMAGE_TAG}${NC}\n"
    printf "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
    echo ""
}

print_status() { printf "${GREEN}[INSTALL]${NC} %s\n" "$1"; }
print_error() { printf "${RED}[ERROR]${NC} %s\n" "$1" >&2; }
print_warning() { printf "${YELLOW}[WARNING]${NC} %s\n" "$1"; }
print_info() { printf "${BLUE}[INFO]${NC} %s\n" "$1"; }
print_section() { 
    echo ""
    printf "${BOLD}${GREEN}▶ %s${NC}\n" "$1"
    printf "${GREEN}────────────────────────────────────────────────────────────${NC}\n"
}

# Check prerequisites
check_prerequisites() {
    print_section "Checking Prerequisites"
    
    local errors=0
    
    # Check Docker
    if command -v docker >/dev/null 2>&1; then
        local docker_version=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
        print_status "✓ Docker installed (version $docker_version)"
    else
        print_error "✗ Docker is not installed"
        print_info "  Install from: https://docs.docker.com/get-docker/"
        ((errors++))
    fi
    
    # Check Docker Compose
    if docker compose version >/dev/null 2>&1; then
        local compose_version=$(docker compose version --short)
        print_status "✓ Docker Compose installed (version $compose_version)"
    else
        print_error "✗ Docker Compose v2 is not installed"
        print_info "  Install from: https://docs.docker.com/compose/install/"
        ((errors++))
    fi
    
    # Check if Docker daemon is running
    if docker info >/dev/null 2>&1; then
        print_status "✓ Docker daemon is running"
    else
        print_error "✗ Docker daemon is not running"
        print_info "  Start Docker service: sudo systemctl start docker"
        ((errors++))
    fi
    
    # Check git
    if command -v git >/dev/null 2>&1; then
        print_status "✓ Git installed"
    else
        print_warning "⚠ Git is not installed (optional but recommended)"
    fi
    
    # Check yq (required for custom registry configuration)
    if command -v yq >/dev/null 2>&1; then
        local yq_version=$(yq --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
        print_status "✓ yq installed (version $yq_version)"
    else
        print_warning "⚠ yq is not installed (required for custom registry configuration)"
        print_info "  Install: wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64"
        print_info "           chmod +x /usr/local/bin/yq"
    fi
    
    if [[ $errors -gt 0 ]]; then
        print_error "Prerequisites check failed. Please install missing components."
        exit 1
    fi
    
    print_status "All prerequisites met!"
    return 0
}

# Build Docker images
build_images() {
    print_section "Building Docker Images"
    
    if [[ ! -f "images/build.sh" ]]; then
        print_error "Image build script not found at images/build.sh"
        exit 1
    fi
    
    # Make build script executable
    chmod +x images/build.sh
    
    # Run the build script
    print_status "Building all required Docker images..."
    print_info "This may take several minutes on first run..."
    echo ""
    
    if ./images/build.sh all; then
        print_status "✓ All Docker images built successfully"
    else
        print_error "✗ Failed to build Docker images"
        print_info "Check the error messages above and try again"
        exit 1
    fi
}

# Configure custom registry
configure_custom_registry() {
    print_section "Custom Registry Configuration (Optional)"
    
    print_info "You can configure custom Docker registries for caching."
    print_info "This is useful for corporate environments with private registries."
    echo ""
    
    read -p "Do you want to configure custom registries? [y/N]: " configure_registry
    
    if [[ "${configure_registry}" =~ ^[Yy]$ ]]; then
        echo ""
        read -p "Enter your custom registry URLs (e.g., proget.company.com or registry1.com,registry2.com): " custom_registry
        
        if [[ -n "${custom_registry}" ]]; then
            # Create docker-proxy .env file directly in the installed location
            DOCKER_PROXY_ENV="/usr/local/share/ai-agents-sandbox/docker-proxy/.env"
            DOCKER_COMPOSE_FILE="/usr/local/share/ai-agents-sandbox/docker-proxy/docker-compose.yaml"
            
            print_status "Configuring custom registry: ${custom_registry}"
            
            # Create the .env content
            ENV_CONTENT="# Custom Docker Registry Configuration
ADDITIONAL_REGISTRIES=${custom_registry}
REGISTRY_WHITELIST=${custom_registry}"
            
            # Ask about custom docker-registry-proxy image with CA certificates
            echo ""
            print_info "If your registry uses self-signed or internal CA certificates,"
            print_info "you may need a custom docker-registry-proxy image with embedded CA certs."
            echo ""
            read -p "Do you have a custom docker-registry-proxy image with CA certificates? [y/N]: " has_custom_image
            
            if [[ "${has_custom_image}" =~ ^[Yy]$ ]]; then
                echo ""
                read -p "Enter the custom image name (e.g., myregistry/docker-registry-proxy:custom): " custom_image
                
                if [[ -n "${custom_image}" ]]; then
                    print_status "Will use custom image: ${custom_image}"
                    
                    # Add to env file for docker-compose to use
                    ENV_CONTENT="${ENV_CONTENT}
# Custom docker-registry-proxy image (with CA certificates)
DOCKER_REGISTRY_PROXY_IMAGE=${custom_image}"
                    
                    print_status "✓ Custom proxy image configured: ${custom_image}"
                fi
            fi
            
            # Create destination directory if needed and write the config
            if [[ $EUID -ne 0 ]]; then
                # Need sudo to create directory and write to system location
                sudo mkdir -p "/usr/local/share/ai-agents-sandbox/docker-proxy"
                echo "${ENV_CONTENT}" | sudo tee "${DOCKER_PROXY_ENV}" > /dev/null
            else
                mkdir -p "/usr/local/share/ai-agents-sandbox/docker-proxy"
                cat > "${DOCKER_PROXY_ENV}" << EOF
${ENV_CONTENT}
EOF
            fi
            
            print_status "✓ Custom registry configured: ${custom_registry}"
            print_info "Registry will be added to Docker proxy cache configuration"
        else
            print_warning "No registry URL provided, skipping configuration"
        fi
    else
        print_info "Skipping custom registry configuration"
    fi
    echo ""
}

# Install host scripts
install_host_scripts() {
    print_section "Installing Host Scripts"
    
    print_info "The following scripts will be installed to /usr/local/bin:"
    print_info "  • ai-sbx-create-task-worktree    - Create git worktree for new tasks"
    print_info "  • ai-sbx-remove-task-worktree    - Remove task worktrees"
    print_info "  • ai-sbx-connect-task-worktree   - Connect to existing task worktrees"
    print_info "  • ai-sbx-notify-watch            - Desktop notification watcher (optional)"
    print_info "  • ai-sbx-init-project            - Initialize project with Docker proxy"
    echo ""
    print_info "Additional setup:"
    print_info "  • Creates 'local-ai-team' group (GID 3000) for file sharing"
    print_info "  • Creates ~/.ai_agents_sandbox/notifications for alerts"
    print_info "  • Creates ~/.ai_agents_sandbox/projects for statistics"
    print_info "  • Installs base Docker Compose template"
    print_info "  • Sets up Docker proxy for transparent image caching"
    echo ""
    
    if [[ ! -f "host/install.sh" ]]; then
        print_error "Host install script not found at host/install.sh"
        exit 1
    fi
    
    # Make install script executable
    chmod +x host/install.sh
    
    # Check if we need sudo
    if [[ $EUID -ne 0 ]]; then
        print_warning "Root access required to install system scripts"
        print_info "You may be prompted for your sudo password..."
        echo ""
        
        if sudo -v; then
            sudo ./host/install.sh
        else
            print_error "Failed to obtain root access"
            exit 1
        fi
    else
        ./host/install.sh
    fi
    
    print_status "✓ Host scripts installed successfully"
}\

# Verify installation
verify_installation() {
    print_section "Verifying Installation"
    
    local errors=0
    
    # Check Docker images
    for image_name in "ai-agents-sandbox/devcontainer" "ai-agents-sandbox/tinyproxy-base" "ai-agents-sandbox/tinyproxy" "ai-agents-sandbox/tinyproxy-registry" "ai-agents-sandbox/docker-dind" "ai-agents-sandbox/devcontainer-dotnet" "ai-agents-sandbox/devcontainer-golang"; do
        image_full="${image_name}:${IMAGE_TAG}"
        if docker image inspect "$image_full" >/dev/null 2>&1; then
            print_status "✓ Docker image found: $image_full"
        else
            print_error "✗ Docker image missing: $image_full"
            ((errors++))
        fi
    done
    
    # Check installed scripts
    for script in ai-sbx-create-task-worktree ai-sbx-remove-task-worktree ai-sbx-connect-task-worktree ai-sbx-notify-watch ai-sbx-init-project; do
        if command -v "$script" >/dev/null 2>&1; then
            print_status "✓ Script installed: $script"
        else
            print_error "✗ Script not found: $script"
            ((errors++))
        fi
    done
    
    # Check templates
    if [[ -d "/usr/local/share/ai-agents-sandbox" ]]; then
        print_status "✓ Templates installed"
    else
        print_error "✗ Templates not found"
        ((errors++))
    fi
    
    # Check local-ai-team group
    if getent group 3000 >/dev/null 2>&1; then
        print_status "✓ Local-ai-team group (GID 3000) exists"
    else
        print_warning "⚠ Local-ai-team group not created (may need to run as root)"
    fi
    
    if [[ $errors -gt 0 ]]; then
        print_error "Installation verification failed"
        return 1
    fi
    
    print_status "✓ Installation verified successfully!"
    return 0
}

# Show quick start guide
show_quickstart() {
    print_section "Installation Complete!"
    
    printf "\n"
    printf "${BOLD}Quick Start Guide:${NC}\n"
    printf "\n"
    printf "${BOLD}For new projects:${NC}\n"
    printf "1. Copy the template to your project:\n"
    printf "   ${GREEN}cp -r .devcontainer.example /path/to/project/.devcontainer${NC}\n"
    printf "\n"
    printf "2. Initialize project permissions:\n"
    printf "   ${GREEN}cd /path/to/project/.devcontainer${NC}\n"
    printf "   ${GREEN}./initialize.sh${NC}\n"
    printf "\n"
    printf "3. Configure (optional):\n"
    printf "   - Edit: ${BLUE}.devcontainer/.env${NC} for PROJECT_NAME and proxy\n"
    printf "   - Add domains to: ${BLUE}.devcontainer/whitelist.txt${NC}\n"
    printf "\n"
    printf "4. Open in your IDE:\n"
    printf "   ${BOLD}PyCharm:${NC} Settings → Python Interpreter → Docker Compose → devcontainer\n"
    printf "   ${BOLD}VS Code:${NC} Click \"Reopen in Container\"\n"
    printf "\n"
    printf "${BOLD}For this repository:${NC}\n"
    printf "   Just open in PyCharm/VS Code - ${GREEN}.devcontainer/${NC} is ready!\n"
    printf "\n"
    printf "${BOLD}Available commands:${NC}\n"
    printf "   ${GREEN}ai-sbx-create-task-worktree \"task description\"${NC} - Create task branch\n"
    printf "   ${GREEN}ai-sbx-remove-task-worktree [worktree/branch]${NC} - Remove task worktree\n"
    printf "   ${GREEN}ai-sbx-connect-task-worktree${NC} - Connect to existing task worktree\n"
    printf "   ${GREEN}ai-sbx-notify-watch &${NC} - Enable desktop notifications\n"
    printf "   ${GREEN}ai-sbx-init-project [path]${NC} - Initialize project permissions\n"
    printf "\n"
    printf "${BOLD}For more help:${NC}\n"
    printf "   - Documentation: ${BLUE}README.md${NC}\n"
    printf "   - PyCharm guide: ${BLUE}docs/PYCHARM.md${NC}\n"
    printf "   - Development: ${BLUE}docs/DEVELOPMENT.md${NC}\n"
    printf "\n"
    printf "${BOLD}${YELLOW}Important:${NC} Log out and back in for group membership changes to take effect.\n"
    printf "\n"
}

# Main installation flow
main() {
    print_header
    
    # Parse arguments
    SKIP_BUILD=false
    SKIP_SCRIPTS=false
    VERIFY_ONLY=false
    
    for arg in "$@"; do
        case $arg in
            --skip-build)
                SKIP_BUILD=true
                ;;
            --skip-scripts)
                SKIP_SCRIPTS=true
                ;;
            --verify)
                VERIFY_ONLY=true
                ;;
            --help|-h)
                cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --skip-build     Skip building Docker images
  --skip-scripts   Skip installing host scripts
  --verify         Only verify existing installation
  --help, -h       Show this help message

Examples:
  $0                    # Full installation
  $0 --skip-build       # Install scripts only (images already built)
  $0 --verify           # Verify installation
  
EOF
                exit 0
                ;;
            *)
                print_error "Unknown option: $arg"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    if [[ "$VERIFY_ONLY" == true ]]; then
        verify_installation
        exit $?
    fi
    
    # Configure custom registry (before building images)
    configure_custom_registry
    
    # Build Docker images
    if [[ "$SKIP_BUILD" != true ]]; then
        build_images
    else
        print_warning "Skipping Docker image build (--skip-build specified)"
    fi
    
    # Install host scripts
    if [[ "$SKIP_SCRIPTS" != true ]]; then
        install_host_scripts
    else
        print_warning "Skipping host script installation (--skip-scripts specified)"
    fi
    
    # Verify installation
    if verify_installation; then
        show_quickstart
        exit 0
    else
        print_error "Installation completed with errors. Please check the messages above."
        exit 1
    fi
}

# Run main function
main "$@"