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
            
            # Create docker-proxy directory if it doesn't exist
            mkdir -p "resources/docker-proxy"
            
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
            mkdir -p "resources/docker-proxy"
            cat > "resources/docker-proxy/.env" << EOF
${ENV_CONTENT}
EOF
            
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

# Install Python CLI
install_python_cli() {
    print_section "Installing Python CLI"
    
    print_info "The ai-sbx Python CLI will be installed with the following commands:"
    print_info "  • ai-sbx init          - Initialize project with devcontainer"
    print_info "  • ai-sbx worktree      - Manage git worktrees for tasks"
    print_info "  • ai-sbx docker        - Manage Docker containers and images"
    print_info "  • ai-sbx notify        - Start notification watcher"
    print_info "  • ai-sbx doctor        - Diagnose and fix setup issues"
    print_info "  • ai-sbx upgrade       - Upgrade to latest version"
    echo ""
    
    # Check for Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed"
        print_info "Please install Python 3.9 or later"
        exit 1
    fi
    
    # Install Python package
    print_status "Installing ai-sbx Python package..."
    
    # Check if uv is available (preferred)
    if command -v uv &> /dev/null; then
        print_status "Using uv to install ai-sbx..."
        uv pip install --system -e .
        print_status "✓ Python CLI installed with uv"
    elif command -v pip3 &> /dev/null; then
        print_status "Using pip to install ai-sbx..."
        pip3 install -e .
        print_status "✓ Python CLI installed with pip"
    else
        print_error "Neither uv nor pip3 is available"
        print_info "Please install pip3 or uv to continue"
        exit 1
    fi
    
    # Verify installation
    if command -v ai-sbx &> /dev/null; then
        print_status "✓ AI Agents Sandbox CLI installed successfully"
    else
        print_error "Installation verification failed - ai-sbx command not found"
        print_info "You may need to add Python scripts directory to your PATH"
        print_info "Try: export PATH=\"\$HOME/.local/bin:\$PATH\""
        exit 1
    fi
}

# Setup system configuration
setup_system_config() {
    print_section "Setting up System Configuration"
    
    # Create local-ai-team group if it doesn't exist
    DEV_GID=3000
    if ! getent group local-ai-team >/dev/null 2>&1; then
        print_status "Creating local-ai-team group (GID $DEV_GID) for file sharing..."
        
        if [[ $EUID -ne 0 ]]; then
            print_info "Root access required to create group"
            if sudo groupadd -g $DEV_GID local-ai-team 2>/dev/null; then
                print_status "✓ Group 'local-ai-team' created"
            else
                print_warning "Could not create group (may already exist)"
            fi
        else
            groupadd -g $DEV_GID local-ai-team 2>/dev/null || true
            print_status "✓ Group 'local-ai-team' created"
        fi
    else
        print_status "✓ Group 'local-ai-team' already exists"
    fi
    
    # Add current user to local-ai-team group
    CURRENT_USER="${SUDO_USER:-$USER}"
    if [[ -n "$CURRENT_USER" ]] && [[ "$CURRENT_USER" != "root" ]]; then
        print_status "Adding $CURRENT_USER to local-ai-team group..."
        
        if [[ $EUID -ne 0 ]]; then
            if sudo usermod -aG local-ai-team "$CURRENT_USER" 2>/dev/null; then
                print_status "✓ User added to local-ai-team group"
            else
                print_warning "Could not add user to group"
            fi
        else
            usermod -aG local-ai-team "$CURRENT_USER" 2>/dev/null || true
            print_status "✓ User added to local-ai-team group"
        fi
    fi
    
    # Create notification directories
    if [[ -n "$CURRENT_USER" ]] && [[ "$CURRENT_USER" != "root" ]]; then
        USER_HOME=$(eval echo ~$CURRENT_USER)
        AI_SBX_DIR="${USER_HOME}/.ai_agents_sandbox"
        NOTIFICATION_DIR="$AI_SBX_DIR/notifications"
        PROJECTS_DIR="$AI_SBX_DIR/projects"
        
        print_status "Creating AI Agents Sandbox directories..."
        
        # Create directories
        mkdir -p "$NOTIFICATION_DIR"
        mkdir -p "$PROJECTS_DIR"
        
        # Set ownership
        if [[ $EUID -eq 0 ]]; then
            chown -R "$CURRENT_USER:$CURRENT_USER" "$AI_SBX_DIR"
        fi
        
        print_status "✓ Notification directories created"
    fi
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
    
    # Check installed Python CLI
    if command -v "ai-sbx" >/dev/null 2>&1; then
        print_status "✓ Python CLI installed: ai-sbx"
    else
        print_error "✗ Python CLI not found: ai-sbx"
        ((errors++))
    fi
    
    # Check resources directory
    if [[ -d "resources" ]]; then
        print_status "✓ Resources directory exists"
    else
        print_error "✗ Resources directory not found"
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
    printf "   ${GREEN}ai-sbx init [path]${NC} - Initialize project\n"
    printf "   ${GREEN}ai-sbx worktree create \"task description\"${NC} - Create task branch\n"
    printf "   ${GREEN}ai-sbx worktree remove [name]${NC} - Remove task worktree\n"
    printf "   ${GREEN}ai-sbx worktree connect${NC} - Connect to existing task\n"
    printf "   ${GREEN}ai-sbx notify${NC} - Enable desktop notifications\n"
    printf "   ${GREEN}ai-sbx doctor${NC} - Diagnose setup issues\n"
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
    
    # Install Python CLI
    if [[ "$SKIP_SCRIPTS" != true ]]; then
        install_python_cli
        setup_system_config
    else
        print_warning "Skipping Python CLI installation (--skip-scripts specified)"
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