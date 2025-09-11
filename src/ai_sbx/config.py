"""Configuration management for AI Agents Sandbox."""

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from platformdirs import user_config_dir, user_data_dir
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class IDE(str, Enum):
    """Supported IDEs."""

    VSCODE = "vscode"
    PYCHARM = "pycharm"
    RIDER = "rider"
    GOLAND = "goland"
    DEVCONTAINER = "devcontainer"
    CLAUDE = "claude"


class ImageVariant(str, Enum):
    """Available image variants."""

    BASE = "devcontainer"  # Maps to ai-agents-sandbox/devcontainer
    DOTNET = "devcontainer-dotnet"
    GOLANG = "devcontainer-golang"
    # Future additions
    # RUST = "devcontainer-rust"
    # JAVA = "devcontainer-java"


class ProxyConfig(BaseModel):
    """Proxy configuration."""

    enabled: bool = True
    upstream: Optional[str] = None
    no_proxy: list[str] = Field(default_factory=list)
    whitelist_domains: list[str] = Field(default_factory=list)

    @field_validator("upstream")
    @classmethod
    def validate_upstream(cls, v: Optional[str]) -> Optional[str]:
        """Validate upstream proxy URL."""
        if v and not (v.startswith("http://") or v.startswith("socks5://")):
            raise ValueError("Upstream proxy must start with http:// or socks5://")
        return v


class DockerConfig(BaseModel):
    """Docker configuration."""

    registry_proxy: bool = True
    custom_registries: list[str] = Field(default_factory=list)
    image_prefix: str = "ai-agents-sandbox"
    image_tag: str = "latest"
    build_args: dict[str, str] = Field(default_factory=dict)


class ProjectConfig(BaseModel):
    """Project-specific configuration."""

    name: str
    path: Path
    preferred_ide: IDE = IDE.VSCODE
    variant: ImageVariant = ImageVariant.BASE
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    environment: dict[str, str] = Field(default_factory=dict)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: Path) -> Path:
        """Ensure path is absolute."""
        return v.resolve()


class GlobalConfig(BaseModel):
    """Global AI Agents Sandbox configuration."""

    version: str = "2.0.0"
    group_name: str = "local-ai-team"
    group_gid: int = 3000
    user_uid: int = 1001
    default_ide: IDE = IDE.VSCODE
    default_variant: ImageVariant = Field(default=ImageVariant.BASE)
    docker: DockerConfig = Field(default_factory=DockerConfig)
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    templates_dir: Optional[Path] = None

    def save(self, path: Optional[Path] = None) -> None:
        """Save configuration to file."""
        if path is None:
            path = get_global_config_path()

        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            yaml.dump(self.model_dump(mode="json"), f, default_flow_style=False)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "GlobalConfig":
        """Load configuration from file."""
        if path is None:
            path = get_global_config_path()

        if not path.exists():
            # Return default config if file doesn't exist
            config = cls()
            config.save(path)
            return config

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="AI_SBX_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Environment variables
    debug: bool = False
    verbose: bool = False
    no_color: bool = False

    # Paths
    config_dir: Path = Field(default_factory=lambda: Path(user_config_dir("ai-agents-sandbox")))
    data_dir: Path = Field(default_factory=lambda: Path(user_data_dir("ai-agents-sandbox")))
    templates_dir: Optional[Path] = None

    # Docker settings
    docker_host: Optional[str] = None
    docker_buildkit: bool = True

    # Feature flags
    use_sudo: bool = True
    interactive: bool = True
    dry_run: bool = False

    @property
    def global_config_path(self) -> Path:
        """Path to global configuration file."""
        return self.config_dir / "config.yaml"

    @property
    def templates_path(self) -> Path:
        """Path to templates directory."""
        if self.templates_dir:
            return self.templates_dir
        return self.data_dir / "templates"


def get_global_config_path() -> Path:
    """Get the path to the global configuration file."""
    return Path(user_config_dir("ai-agents-sandbox")) / "config.yaml"


def get_project_config_path(project_dir: Path) -> Path:
    """Get the path to a project's configuration file."""
    return project_dir / ".devcontainer" / "ai-sbx.yaml"


def load_project_config(project_dir: Path) -> Optional[ProjectConfig]:
    """Load project configuration if it exists."""
    config_path = get_project_config_path(project_dir)

    if not config_path.exists():
        return None

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    # Ensure path is set
    if "path" not in data:
        data["path"] = str(project_dir)

    return ProjectConfig(**data)


def save_project_config(config: ProjectConfig) -> None:
    """Save project configuration."""
    config_path = get_project_config_path(config.path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config.model_dump(mode="json"), f, default_flow_style=False)


def get_default_whitelist_domains() -> list[str]:
    """Get the default whitelist domains."""
    return [
        # Package registries
        "pypi.org",
        "files.pythonhosted.org",
        "registry.npmjs.org",
        "registry.yarnpkg.com",
        "rubygems.org",
        "crates.io",
        "pkg.go.dev",
        "proxy.golang.org",
        "sum.golang.org",
        "nuget.org",
        "api.nuget.org",
        "packages.nuget.org",
        # Source control
        "github.com",
        "api.github.com",
        "raw.githubusercontent.com",
        "github.githubassets.com",
        "gitlab.com",
        "bitbucket.org",
        # Development tools
        "docker.io",
        "registry.docker.io",
        "hub.docker.com",
        "quay.io",
        "gcr.io",
        "ghcr.io",
        "cdn.jsdelivr.net",
        "unpkg.com",
        "cdnjs.cloudflare.com",
        # Documentation
        "docs.python.org",
        "docs.npmjs.com",
        "docs.docker.com",
        "docs.github.com",
        "developer.mozilla.org",
        "stackoverflow.com",
        # AI/ML
        "huggingface.co",
        "cdn-lfs.huggingface.co",
        "anthropic.com",
        "api.anthropic.com",
    ]
