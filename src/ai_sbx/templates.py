"""Template management for AI Agents Sandbox."""

import hashlib
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, Template

from ai_sbx.config import BaseImage, ProjectConfig, get_default_whitelist_domains
from ai_sbx.utils import logger


def generate_unique_subnet(project_name: str) -> tuple[str, str]:
    """Generate a unique subnet and DNS IP based on project name.

    Uses a hash of the project name to generate a deterministic subnet
    in the 172.16-31.x.0/24 range to avoid conflicts with other worktrees.

    Args:
        project_name: The project name to hash

    Returns:
        Tuple of (subnet, dns_ip) e.g. ("172.18.42.0/24", "172.18.42.53")
    """
    # Create a hash of the project name
    hash_bytes = hashlib.md5(project_name.encode()).digest()

    # Use first two bytes for second and third octet
    # Second octet: 16-31 (16 values) to stay in private 172.16.0.0/12 range
    second_octet = 16 + (hash_bytes[0] % 16)
    # Third octet: 0-255
    third_octet = hash_bytes[1]

    # Total unique subnets: 16 * 256 = 4096 different /24 subnets
    subnet = f"172.{second_octet}.{third_octet}.0/24"
    dns_ip = f"172.{second_octet}.{third_octet}.53"

    return subnet, dns_ip


def get_docker_image_name(base_image: BaseImage) -> str:
    """Map base image type to actual Docker image name."""
    mapping = {
        BaseImage.BASE: "devcontainer",
        BaseImage.DOTNET: "devcontainer-dotnet",
        BaseImage.GOLANG: "devcontainer-golang",
    }
    return mapping.get(base_image, "devcontainer")


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
        custom_dockerfile: bool = False,
    ) -> bool:
        """Generate all project files from templates.

        Args:
            output_dir: Output directory (.devcontainer)
            config: Project configuration
            force: Overwrite existing files
            custom_dockerfile: Whether to create a custom Dockerfile

        Returns:
            True if all files were created successfully
        """
        success = True

        # Files to generate (NOT docker-compose.yaml!)
        files = {
            "devcontainer.json": self._generate_devcontainer_json(config),
            ".env": self._generate_env_file(config),
            ".gitignore": self._generate_gitignore(),
            "docker-compose.override.yaml": self._generate_user_override(config),
            "init.sh": self._generate_init_script(config),
            "ai-sbx.yaml.template": self._generate_config_template(config),
        }

        # Only add Dockerfile if not using a custom image
        if custom_dockerfile or not config.environment.get("CUSTOM_DOCKER_IMAGE"):
            files["Dockerfile"] = self._generate_dockerfile(config)

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

    def _generate_gitignore(self) -> str:
        """Generate .gitignore file."""
        return """# Local environment configuration
.env
.user.env

# Local project configuration (contains machine-specific paths)
ai-sbx.yaml

# Security-sensitive initialization script (contains secrets/credentials)
init.secure.sh

# NOTE: docker-compose.base.yaml is tracked - uses environment variables for system-specific paths
# NOTE: docker-compose.override.yaml is tracked - contains common project overrides
"""

    def _generate_user_override(self, config: ProjectConfig) -> str:
        """Generate docker-compose.override.yaml with common project overrides."""
        # Check if Claude settings should be mounted
        mount_claude = config.environment.get("MOUNT_CLAUDE_SETTINGS") == "true"
        # Check if custom Docker image is specified
        custom_image = config.environment.get("CUSTOM_DOCKER_IMAGE")
        # Check if custom DinD image is specified
        custom_dind_image = config.environment.get("CUSTOM_DIND_IMAGE")

        base_content = """# Common Project Docker Compose Overrides
# This file is committed to git and shared across the team
# Add project-specific configuration here

services:"""

        # Add custom DinD image if specified
        if custom_dind_image:
            base_content += f"""
  docker:
    # Using custom Docker-in-Docker image
    image: {custom_dind_image}

  tinyproxy-devcontainer:
    image: ai-agents-sandbox/tinyproxy:1.0.0"""
        else:
            base_content += """
  tinyproxy-devcontainer:
    image: ai-agents-sandbox/tinyproxy:1.0.0"""

        # Add proxy configuration if present
        if config.proxy and config.proxy.enabled:
            base_content += """
    environment:"""

            # Add whitelist domains
            if config.proxy.whitelist_domains:
                domains_str = " ".join(config.proxy.whitelist_domains)
                base_content += f"""
      USER_WHITELIST_DOMAINS: "{domains_str}" """
            else:
                base_content += """
      # Add your project-specific domains here (comma or space separated)
      USER_WHITELIST_DOMAINS: ""  # e.g. "api.example.com,cdn.example.com" """

            # Add upstream proxy if configured
            if config.proxy.upstream:
                base_content += f"""
      UPSTREAM_PROXY: "{config.proxy.upstream}" """

            # Add no_proxy domains if configured
            if config.proxy.no_proxy:
                no_proxy_str = ",".join(config.proxy.no_proxy)
                base_content += f"""
      NO_UPSTREAM: "{no_proxy_str}" """
        else:
            base_content += """
    environment:
      # Add your project-specific domains here (comma or space separated)
      USER_WHITELIST_DOMAINS: ""  # e.g. "api.example.com,cdn.example.com" """

        base_content += """

  devcontainer:"""

        if custom_image:
            # Use the custom image directly, no build needed
            base_content += f"""
    # Using custom Docker image (no Dockerfile needed)
    image: {custom_image}"""
        else:
            # Use build configuration for standard images or custom Dockerfile
            base_content += """
    # Building from Dockerfile
    build:
      context: .
      dockerfile: Dockerfile"""

        if mount_claude:
            base_content += """
    volumes:
      # Mount user's Claude settings (readonly) - will be copied on startup
      - ${HOME}/.claude:/host/.claude:ro
    environment:
      # Flag to copy Claude settings on startup
      - COPY_CLAUDE_SETTINGS=true"""
        else:
            base_content += """
    # Example: Add custom environment variables
    # environment:
    #   - MY_CUSTOM_VAR=value

    # Example: Mount additional volumes
    # volumes:
    #   - ~/my-data:/data"""

        return base_content + "\n"

    def _generate_devcontainer_json(self, config: ProjectConfig) -> str:
        """Generate devcontainer.json content."""
        template = """{
    "name": "{{ config.name }} - AI Agents Sandbox",
    "dockerComposeFile": ["docker-compose.base.yaml", "docker-compose.override.yaml"],
    "service": "devcontainer",
    "workspaceFolder": "/workspace",
    "shutdownAction": "stopCompose",
    "containerUser": "claude",
    "updateRemoteUserUID": false,
    "initializeCommand": ".devcontainer/init.sh \\"${localWorkspaceFolder}\\"",
    "postCreateCommand": "/home/claude/scripts/non-root-post-create.sh",
    "containerEnv": {
        "TERM": "xterm-256color",
        "COLORTERM": "truecolor"
    },
    "remoteEnv": {
        "NODE_OPTIONS": "--max-old-space-size=4096",
        "CLAUDE_CONFIG_DIR": "/home/claude/.claude",
        "POWERLEVEL9K_DISABLE_GITSTATUS": "true"
    },

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

    "forwardPorts": [],

    "mounts": []
}
"""
        return Template(template).render(config=config)

    def _generate_dockerfile(self, config: ProjectConfig) -> str:
        """Generate Dockerfile content."""
        docker_image = get_docker_image_name(config.base_image)
        template = """# Project-specific Dockerfile
# Extends the AI Agents Sandbox {{ docker_image }} image

FROM ai-agents-sandbox/{{ docker_image }}:{{ config.docker.image_tag }}

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
        return Template(template).render(config=config, docker_image=docker_image)

    def _generate_env_file(self, config: ProjectConfig) -> str:
        """Generate .env file content with only Docker runtime variables."""
        # Use directory name (not config.name) for unique identification
        # This ensures each worktree gets unique network settings
        # even though they share the same ai-sbx.yaml with same config.name
        dir_name = config.path.name

        # Generate unique subnet for this project/worktree to avoid network conflicts
        subnet, dns_ip = generate_unique_subnet(dir_name)

        template = """# Docker Compose Runtime Configuration
# This file is auto-generated from ai-sbx.yaml
# To modify settings, edit ai-sbx.yaml and run 'ai-sbx init update'

# Required for Docker Compose
PROJECT_DIR={{ config.path }}
PROJECT_NAME={{ dir_name }}
COMPOSE_PROJECT_NAME={{ dir_name }}

# Network configuration (unique per project/worktree to avoid conflicts)
NETWORK_SUBNET={{ subnet }}
DNS_PROXY_IP={{ dns_ip }}

# Docker image version
IMAGE_TAG={{ config.docker.image_tag }}

{% if config.proxy.upstream -%}
# Proxy configuration (from ai-sbx.yaml)
UPSTREAM_PROXY={{ config.proxy.upstream }}
{% endif -%}

{% if config.proxy.no_proxy -%}
NO_UPSTREAM={{ ' '.join(config.proxy.no_proxy) }}
{% endif -%}

{% if config.proxy.whitelist_domains -%}
# Additional whitelist domains (from ai-sbx.yaml)
USER_WHITELIST_DOMAINS={{ ' '.join(config.proxy.whitelist_domains) }}
{% endif -%}

{% if config.docker.custom_registries -%}
# Custom Docker registries (from ai-sbx.yaml)
ADDITIONAL_REGISTRIES={{ ' '.join(config.docker.custom_registries) }}
{% endif -%}

# Custom environment variables
{% for key, value in config.environment.items() -%}
{{ key }}={{ value }}
{% endfor -%}
"""
        return Template(template).render(
            config=config, dir_name=dir_name, subnet=subnet, dns_ip=dns_ip
        )

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
# AI Agents Sandbox - Project Initialization Script
# This script is called automatically by VS Code when opening the project
#
# Example of manual usage:
#   .devcontainer/init.sh /path/to/project

PROJECT_DIR="${1:-$(pwd)}"

# Initialize the worktree environment
ai-sbx init worktree "$PROJECT_DIR"
"""
        return Template(template).render(config=config)

    def _generate_config_template(self, config: ProjectConfig) -> str:
        """Generate ai-sbx.yaml.template with shareable configuration.

        This template contains project defaults without machine-specific paths.
        Other users can use this to generate their own ai-sbx.yaml.
        """
        template = """# AI Agents Sandbox - Project Configuration Template
# This file contains shareable project defaults
# When cloning this repository, run 'ai-sbx init project' to generate your local ai-sbx.yaml

# Project name (used for Docker Compose project name)
name: {{ config.name }}

# NOTE: 'path' will be set automatically to your local project path

# Development environment preferences
preferred_ide: {{ config.preferred_ide.value }}
base_image: {{ config.base_image.value }}

# Main branch (for worktree filtering)
{% if config.main_branch -%}
main_branch: {{ config.main_branch }}
{% else -%}
# main_branch: main  # Uncomment and set if needed
{% endif -%}

# Proxy configuration (always enabled for security)
proxy:
  enabled: true
  {% if config.proxy.upstream -%}
  # Upstream proxy (adjust for your environment)
  upstream: {{ config.proxy.upstream }}
  {% else -%}
  # Uncomment and configure if you need an upstream proxy
  # upstream: socks5://host.gateway:8888
  {% endif -%}

  {% if config.proxy.no_proxy -%}
  # Domains that bypass the upstream proxy
  no_proxy:
  {% for domain in config.proxy.no_proxy -%}
    - {{ domain }}
  {% endfor -%}
  {% else -%}
  # Domains that bypass the upstream proxy
  # no_proxy:
  #   - github.com
  #   - gitlab.com
  {% endif -%}

  {% if config.proxy.whitelist_domains -%}
  # Additional domains to allow through the proxy
  whitelist_domains:
  {% for domain in config.proxy.whitelist_domains -%}
    - {{ domain }}
  {% endfor -%}
  {% else -%}
  # Additional domains to allow through the proxy
  # whitelist_domains:
  #   - api.myproject.com
  {% endif %}

# Docker configuration
docker:
  image_tag: {{ config.docker.image_tag }}
  {% if config.docker.custom_registries -%}
  # Custom Docker registries
  custom_registries:
  {% for registry in config.docker.custom_registries -%}
    - {{ registry }}
  {% endfor -%}
  {% else -%}
  # Custom Docker registries
  # custom_registries:
  #   - my.registry.com
  {% endif %}

# Environment variables
{% if config.environment -%}
environment:
{% for key, value in config.environment.items() -%}
  {{ key }}: {{ value }}
{% endfor -%}
{% else -%}
# environment:
#   MY_VAR: value
{% endif -%}
"""
        return Template(template).render(config=config)
