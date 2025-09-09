"""Template management for AI Agents Sandbox."""

from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, Template

from ai_sbx.config import ProjectConfig, get_default_whitelist_domains
from ai_sbx.utils import logger


class TemplateManager:
    """Manages templates for project initialization."""

    def __init__(self, templates_dir: Optional[Path] = None):
        """Initialize template manager.

        Args:
            templates_dir: Custom templates directory
        """
        if templates_dir is None:
            # Use bundled templates
            templates_dir = Path(__file__).parent / "templates"

        self.templates_dir = templates_dir
        self.env = Environment(
            loader=FileSystemLoader(str(templates_dir)) if templates_dir.exists() else None,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate_project_files(
        self,
        output_dir: Path,
        config: ProjectConfig,
        force: bool = False,
    ) -> bool:
        """Generate all project files from templates.

        Args:
            output_dir: Output directory (.devcontainer)
            config: Project configuration
            force: Overwrite existing files

        Returns:
            True if all files were created successfully
        """
        success = True

        # Files to generate
        files = {
            "docker-compose.yaml": self._generate_docker_compose(config),
            "devcontainer.json": self._generate_devcontainer_json(config),
            "Dockerfile": self._generate_dockerfile(config),
            ".env": self._generate_env_file(config),
            "whitelist.txt": self._generate_whitelist(config),
            "init.sh": self._generate_init_script(config),
        }

        for filename, content in files.items():
            file_path = output_dir / filename

            if file_path.exists() and not force:
                logger.warning(f"File already exists: {filename}")
                success = False
                continue

            try:
                file_path.write_text(content)
                logger.debug(f"Created: {filename}")

                # Make shell scripts executable
                if filename.endswith(".sh"):
                    file_path.chmod(0o755)

            except Exception as e:
                logger.error(f"Failed to create {filename}: {e}")
                success = False

        return success

    def _generate_docker_compose(self, config: ProjectConfig) -> str:
        """Generate docker-compose.yaml content."""
        template = """
{% set image_repo = 'ai-agents-sandbox/' + ( 'devcontainer-dotnet' if config.variant.value == 'dotnet' else ('devcontainer-golang' if config.variant.value == 'golang' else config.variant.value) ) %}

services:
  devcontainer:
    image: {{ image_repo }}:latest
    container_name: {{ config.name }}-devcontainer
    hostname: {{ config.name }}-dev
    networks:
      - internal
    volumes:
      - {{ config.path }}:/workspace:cached
      - ~/.ai_agents_sandbox/notifications:/home/claude/.ai_agents_sandbox/notifications
      - ~/.ai_agents_sandbox/projects:/home/claude/.ai_agents_sandbox/projects
      - devcontainer-history:/commandhistory
      - docker-certs-client:/certs/client:ro
    environment:
      - PROJECT_NAME={{ config.name }}
      - PROJECT_DIR={{ config.path }}
      - DOCKER_HOST=tcp://docker:2376
      - DOCKER_TLS_VERIFY=1
      - DOCKER_CERT_PATH=/certs/client
{% if config.proxy.enabled %}
      - HTTP_PROXY=http://tinyproxy:8888
      - HTTPS_PROXY=http://tinyproxy:8888
      - http_proxy=http://tinyproxy:8888
      - https_proxy=http://tinyproxy:8888
      - NO_PROXY=localhost,127.0.0.1,docker,docker-registry-proxy
      - no_proxy=localhost,127.0.0.1,docker,docker-registry-proxy
{% endif %}
    depends_on:
{% if config.proxy.enabled %}
      - tinyproxy
{% endif %}
      - docker
    working_dir: /workspace
    command: sleep infinity
    
{% if config.proxy.enabled %}
  tinyproxy:
    image: ai-agents-sandbox/tinyproxy:latest
    container_name: {{ config.name }}-tinyproxy
    hostname: tinyproxy
    networks:
      - internal
      - external
    volumes:
      - ./whitelist.txt:/etc/tinyproxy/filter:ro
    environment:
      - FILTER_FILE=/etc/tinyproxy/filter
      - FILTER_DEFAULT_DENY=Yes
{% if config.proxy.upstream %}
      - UPSTREAM_PROXY={{ config.proxy.upstream }}
{% endif %}
{% if config.proxy.no_proxy %}
      - NO_UPSTREAM={{ ' '.join(config.proxy.no_proxy) }}
{% endif %}
    restart: unless-stopped
{% endif %}

  docker:
    image: ai-agents-sandbox/docker-dind:latest
    container_name: {{ config.name }}-docker
    hostname: docker
    privileged: true
    networks:
      - internal
    volumes:
      - docker-data:/var/lib/docker
      - docker-certs-ca:/certs/ca
      - docker-certs-client:/certs/client
    environment:
      - DOCKER_TLS_CERTDIR=/certs
      - HTTP_PROXY=http://docker-registry-proxy:3128
      - HTTPS_PROXY=http://docker-registry-proxy:3128
      - NO_PROXY=localhost,127.0.0.1
    restart: unless-stopped

  docker-registry-proxy:
    image: rpardini/docker-registry-proxy:latest
    container_name: {{ config.name }}-registry-proxy
    hostname: docker-registry-proxy
    networks:
      - internal
{% if config.proxy.enabled %}
      - external
{% endif %}
    volumes:
      - registry-cache:/docker_mirror_cache
    environment:
      - REGISTRIES={{ ' '.join(config.docker.custom_registries) if config.docker.custom_registries else 'docker.io gcr.io ghcr.io k8s.gcr.io quay.io' }}
      - ENABLE_MANIFEST_CACHE=true
      - MANIFEST_CACHE_PRIMARY_REGEX=.*
{% if config.proxy.enabled and config.proxy.upstream %}
      - HTTP_PROXY={{ config.proxy.upstream }}
      - HTTPS_PROXY={{ config.proxy.upstream }}
{% endif %}
    restart: unless-stopped

networks:
  internal:
    internal: true
    driver: bridge
{% if config.proxy.enabled %}
  external:
    driver: bridge
{% endif %}

volumes:
  devcontainer-history:
  docker-data:
  docker-certs-ca:
  docker-certs-client:
  registry-cache:
"""
        return Template(template).render(config=config)

    def _generate_devcontainer_json(self, config: ProjectConfig) -> str:
        """Generate devcontainer.json content."""
        template = """{
    "name": "{{ config.name }}",
    "dockerComposeFile": "docker-compose.yaml",
    "service": "devcontainer",
    "workspaceFolder": "/workspace",
    "remoteUser": "claude",
    
    "features": {},
    
    "customizations": {
        "vscode": {
            "extensions": [
                "ms-python.python",
                "ms-python.vscode-pylance",
                "ms-azuretools.vscode-docker",
                "github.copilot",
                "eamodio.gitlens",
                "ms-vscode.makefile-tools"
            ],
            "settings": {
                "terminal.integrated.defaultProfile.linux": "zsh",
                "python.defaultInterpreterPath": "/usr/local/bin/python",
                "python.linting.enabled": true,
                "python.linting.pylintEnabled": false,
                "python.linting.flake8Enabled": false,
                "python.formatting.provider": "black",
                "editor.formatOnSave": true,
                "files.trimTrailingWhitespace": true
            }
        }
    },
    
    "postCreateCommand": "/home/claude/scripts/non-root-post-create.sh",
    "postStartCommand": "",
    "postAttachCommand": "",
    
    "forwardPorts": [],
    
    "mounts": [],
    
    "runArgs": []
}
"""
        return Template(template).render(config=config)

    def _generate_dockerfile(self, config: ProjectConfig) -> str:
        """Generate Dockerfile content."""
        template = """# Project-specific Dockerfile
# Extends the AI Agents Sandbox {{ config.variant.value }} image

FROM ai-agents-sandbox/{{ config.variant.value }}:latest

# Switch to root for any additional installations
USER root

# Add any project-specific system packages here
# RUN apt-get update && apt-get install -y \\
#     package1 \\
#     package2 \\
#     && rm -rf /var/lib/apt/lists/*

# Switch back to claude user
USER claude

# Add any project-specific user packages here
# RUN pip install --user package1 package2
# RUN npm install -g package1 package2

# Copy any project-specific configuration
# COPY --chown=claude:local-ai-team ./configs /home/claude/.config

WORKDIR /workspace
"""
        return Template(template).render(config=config)

    def _generate_env_file(self, config: ProjectConfig) -> str:
        """Generate .env file content."""
        template = """# AI Agents Sandbox Project Configuration
# This file is auto-generated. Use 'ai-sbx init' to reconfigure.

# Project settings
PROJECT_NAME={{ config.name }}
PROJECT_DIR={{ config.path }}
COMPOSE_PROJECT_NAME={{ config.name }}

# IDE preference
PREFERRED_IDE={{ config.preferred_ide.value }}

# Image variant
IMAGE_VARIANT={{ config.variant.value }}

{% if config.proxy.upstream -%}
# Proxy configuration
UPSTREAM_PROXY={{ config.proxy.upstream }}
{% endif -%}

{% if config.proxy.no_proxy -%}
NO_UPSTREAM={{ ' '.join(config.proxy.no_proxy) }}
{% endif -%}

{% if config.proxy.whitelist_domains -%}
# Additional whitelist domains (merged with defaults)
USER_WHITELIST_DOMAINS={{ ' '.join(config.proxy.whitelist_domains) }}
{% endif -%}

{% if config.docker.custom_registries -%}
# Custom Docker registries
ADDITIONAL_REGISTRIES={{ ' '.join(config.docker.custom_registries) }}
{% endif -%}

# Add any additional environment variables below
{% for key, value in config.environment.items() -%}
{{ key }}={{ value }}
{% endfor -%}
"""
        return Template(template).render(config=config)

    def _generate_whitelist(self, config: ProjectConfig) -> str:
        """Generate whitelist.txt content."""
        domains = set(get_default_whitelist_domains())

        # Add user-specified domains
        if config.proxy.whitelist_domains:
            domains.update(config.proxy.whitelist_domains)

        # Sort and format
        content = [
            "# AI Agents Sandbox - Proxy Whitelist",
            "# This file contains domains that are allowed through the proxy",
            "# One domain per line, supports wildcards (*)",
            "",
            "# Default domains",
        ]

        for domain in sorted(domains):
            content.append(domain)

        if config.proxy.whitelist_domains:
            content.extend(
                [
                    "",
                    "# User-specified domains",
                ]
            )
            for domain in sorted(config.proxy.whitelist_domains):
                if domain not in get_default_whitelist_domains():
                    content.append(domain)

        return "\n".join(content) + "\n"

    def _generate_init_script(self, config: ProjectConfig) -> str:
        """Generate init.sh script content."""
        template = """#!/bin/bash
set -euo pipefail

# AI Agents Sandbox - Project Initialization Script
# This script runs when the container is created

echo "Initializing {{ config.name }} development environment..."

# Fix permissions
if [ -d "/workspace" ]; then
    # Ensure group write permissions for collaboration
    find /workspace -type d -exec chmod g+s {} \\; 2>/dev/null || true
fi

# Set up git configuration if needed
if [ -d "/workspace/.git" ]; then
    git config --global --add safe.directory /workspace
fi

# Create project-specific directories
mkdir -p /workspace/.ai_agents_sandbox/{logs,temp,cache}

# Run any project-specific initialization here
# Example: install dependencies, set up databases, etc.

{% if config.variant.value == "python" -%}
# Python project initialization
if [ -f "/workspace/requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install --user -r /workspace/requirements.txt
fi

if [ -f "/workspace/pyproject.toml" ]; then
    echo "Installing Python project..."
    pip install --user -e /workspace
fi
{% endif -%}

{% if config.variant.value == "nodejs" -%}
# Node.js project initialization
if [ -f "/workspace/package.json" ]; then
    echo "Installing Node.js dependencies..."
    npm install
fi
{% endif -%}

{% if config.variant.value == "dotnet" -%}
# .NET project initialization
if [ -f "/workspace/*.sln" ] || [ -f "/workspace/*.csproj" ]; then
    echo "Restoring .NET packages..."
    dotnet restore
fi
{% endif -%}

{% if config.variant.value == "golang" -%}
# Go project initialization
if [ -f "/workspace/go.mod" ]; then
    echo "Downloading Go modules..."
    go mod download
fi
{% endif -%}

echo "Initialization complete!"
"""
        return Template(template).render(config=config)
