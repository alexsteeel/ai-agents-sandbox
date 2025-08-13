#!/bin/bash
set -euo pipefail

# Claude DevContainer System Installer
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
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${BLUE}   AI Agents Sandbox Installer v${VERSION}${NC}"
    echo -e "${BOLD}${BLUE}   Image Tag: ${IMAGE_TAG}${NC}"
    echo -e "${BOLD}${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_status() { echo -e "${GREEN}[INSTALL]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_section() { 
    echo ""
    echo -e "${BOLD}${GREEN}▶ $1${NC}"
    echo -e "${GREEN}$(printf '─%.0s' {1..60})${NC}"
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

# Install host scripts
install_host_scripts() {
    print_section "Installing Host Scripts"
    
    print_info "The following scripts will be installed to /usr/local/bin:"
    print_info "  • claude-task-worktree    - Create git worktree for new tasks"
    print_info "  • claude-notify-watch     - Desktop notification watcher (optional)"
    echo ""
    print_info "Additional setup:"
    print_info "  • Creates 'dev' group (GID 2000) for file sharing"
    print_info "  • Creates ~/.ai_agents_sandbox/notifications for alerts"
    print_info "  • Creates ~/.ai_agents_sandbox/projects for statistics"
    print_info "  • Installs base Docker Compose template"
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
}

# Verify installation
verify_installation() {
    print_section "Verifying Installation"
    
    local errors=0
    
    # Check Docker images
    for image_name in "claudecode/devcontainer" "tinyproxy-whitelist" "tinyproxy-dind" "claudecode/devcontainer-dotnet" "claudecode/devcontainer-golang"; do
        image_full="${image_name}:${IMAGE_TAG}"
        if docker image inspect "$image_full" >/dev/null 2>&1; then
            print_status "✓ Docker image found: $image_full"
        else
            print_error "✗ Docker image missing: $image_full"
            ((errors++))
        fi
    done
    
    # Check installed scripts
    for script in claude-task-worktree claude-notify-watch; do
        if command -v "$script" >/dev/null 2>&1; then
            print_status "✓ Script installed: $script"
        else
            print_error "✗ Script not found: $script"
            ((errors++))
        fi
    done
    
    # Check templates
    if [[ -d "/usr/local/share/claude-devcontainer" ]]; then
        print_status "✓ Templates installed"
    else
        print_error "✗ Templates not found"
        ((errors++))
    fi
    
    # Check dev group
    if getent group 2000 >/dev/null 2>&1; then
        print_status "✓ Dev group (GID 2000) exists"
    else
        print_warning "⚠ Dev group not created (may need to run as root)"
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
    
    cat <<EOF

${BOLD}Quick Start Guide:${NC}

${BOLD}For new projects:${NC}
1. Copy the template to your project:
   ${GREEN}cp -r .devcontainer.example /path/to/project/.devcontainer${NC}

2. Configure (optional):
   - Edit: ${BLUE}.devcontainer/.env${NC} for PROJECT_NAME and proxy
   - Add domains to: ${BLUE}.devcontainer/whitelist.txt${NC}

3. Open in your IDE:
   ${BOLD}PyCharm:${NC} Settings → Python Interpreter → Docker Compose → devcontainer
   ${BOLD}VS Code:${NC} Click "Reopen in Container"

${BOLD}For this repository:${NC}
   Just open in PyCharm/VS Code - ${GREEN}.devcontainer/${NC} is ready!

${BOLD}Available commands:${NC}
   ${GREEN}claude-task-worktree "task description"${NC} - Create task branch
   ${GREEN}claude-notify-watch &${NC} - Enable desktop notifications

${BOLD}For more help:${NC}
   - Documentation: ${BLUE}README.md${NC}
   - PyCharm guide: ${BLUE}docs/PYCHARM.md${NC}
   - Development: ${BLUE}docs/DEVELOPMENT.md${NC}

${BOLD}${YELLOW}Important:${NC} Log out and back in for group membership changes to take effect.

EOF
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