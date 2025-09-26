"""Tests for configuration module."""

import tempfile
from pathlib import Path

import pytest

from ai_sbx.config import (
    IDE,
    BaseImage,
    DockerConfig,
    GlobalConfig,
    ProjectConfig,
    ProxyConfig,
    get_default_whitelist_domains,
    load_project_config,
    save_project_config,
)


class TestGlobalConfig:
    """Test global configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GlobalConfig()

        assert config.version == "2.1.0"
        assert config.group_name == "local-ai-team"
        assert config.group_gid == 3000
        assert config.user_uid == 1001
        assert config.default_ide == IDE.VSCODE
        # Check if default_variant exists, otherwise check default_base_image
        if hasattr(config, "default_variant"):
            assert config.default_variant == BaseImage.BASE
        elif hasattr(config, "default_base_image"):
            assert config.default_base_image == BaseImage.BASE

    def test_save_and_load(self):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            config_path = Path(f.name)

        try:
            # Create and save config
            config = GlobalConfig(
                default_ide=IDE.PYCHARM,
                default_base_image=BaseImage.DOTNET,
            )
            config.save(config_path)

            # Load config
            loaded = GlobalConfig.load(config_path)

            assert loaded.default_ide == IDE.PYCHARM
            assert loaded.default_base_image == BaseImage.DOTNET
            assert loaded.group_gid == 3000

        finally:
            config_path.unlink(missing_ok=True)


class TestProjectConfig:
    """Test project configuration."""

    def test_project_config(self):
        """Test project configuration creation."""
        config = ProjectConfig(
            name="test-project",
            path=Path("/test/project"),
            preferred_ide=IDE.VSCODE,
            base_image=BaseImage.GOLANG,
        )

        assert config.name == "test-project"
        assert config.path == Path("/test/project")
        assert config.preferred_ide == IDE.VSCODE
        assert config.base_image == BaseImage.GOLANG

    def test_path_validation(self):
        """Test path is made absolute."""
        config = ProjectConfig(
            name="test",
            path=Path("relative/path"),
        )

        assert config.path.is_absolute()

    def test_proxy_config(self):
        """Test proxy configuration."""
        config = ProjectConfig(
            name="test",
            path=Path("/test"),
            proxy=ProxyConfig(
                enabled=True,
                upstream="http://host.gateway:3128",
                whitelist_domains=["example.com"],
            ),
        )

        assert config.proxy.enabled
        assert config.proxy.upstream == "http://host.gateway:3128"
        assert "example.com" in config.proxy.whitelist_domains

    def test_invalid_proxy_upstream(self):
        """Test invalid proxy upstream validation."""
        with pytest.raises(ValueError, match="must start with"):
            ProxyConfig(upstream="invalid://proxy")


class TestDockerConfig:
    """Test Docker configuration."""

    def test_docker_config(self):
        """Test Docker configuration."""
        config = DockerConfig(
            registry_proxy=True,
            custom_registries=["registry.example.com"],
            image_prefix="custom",
            image_tag="v1.0.0",
        )

        assert config.registry_proxy
        assert "registry.example.com" in config.custom_registries
        assert config.image_prefix == "custom"
        assert config.image_tag == "v1.0.0"


class TestProjectConfigIO:
    """Test project configuration I/O."""

    def test_save_and_load_project_config(self):
        """Test saving and loading project configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            devcontainer_dir = project_dir / ".devcontainer"
            devcontainer_dir.mkdir()

            # Create config
            config = ProjectConfig(
                name="test-project",
                path=project_dir,
                preferred_ide=IDE.PYCHARM,
                base_image=BaseImage.DOTNET,
                proxy=ProxyConfig(
                    upstream="socks5://localhost:1080",
                    whitelist_domains=["api.example.com"],
                ),
            )

            # Save config
            save_project_config(config)

            # Load config
            loaded = load_project_config(project_dir)

            assert loaded is not None
            assert loaded.name == "test-project"
            assert loaded.preferred_ide == IDE.PYCHARM
            assert loaded.base_image == BaseImage.DOTNET
            assert loaded.proxy.upstream == "socks5://localhost:1080"
            assert "api.example.com" in loaded.proxy.whitelist_domains

    def test_no_legacy_env_support(self):
        """Test that legacy .env files are not loaded."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir)
            devcontainer_dir = project_dir / ".devcontainer"
            devcontainer_dir.mkdir()

            # Create legacy .env file (should be ignored)
            env_file = devcontainer_dir / ".env"
            env_file.write_text(
                """
PROJECT_NAME=legacy-project
PREFERRED_IDE=pycharm
UPSTREAM_PROXY=http://host.gateway:8080
USER_WHITELIST_DOMAINS=api.legacy.com,cdn.legacy.com
"""
            )

            # Load config - should return None since no ai-sbx.yaml exists
            config = load_project_config(project_dir)

            # Legacy .env files are no longer supported
            assert config is None


class TestWhitelist:
    """Test whitelist domains."""

    def test_default_whitelist(self):
        """Test default whitelist domains."""
        domains = get_default_whitelist_domains()

        # Check essential domains are included
        assert "github.com" in domains
        assert "pypi.org" in domains
        assert "registry.npmjs.org" in domains
        assert "docker.io" in domains

        # Check count is reasonable
        assert len(domains) > 20
        assert len(domains) < 100


class TestEnums:
    """Test enum values."""

    def test_ide_enum(self):
        """Test IDE enum values."""
        assert IDE.VSCODE.value == "vscode"
        assert IDE.PYCHARM.value == "pycharm"
        assert IDE.DEVCONTAINER.value == "devcontainer"

        # Test from string
        assert IDE("vscode") == IDE.VSCODE
        assert IDE("pycharm") == IDE.PYCHARM

    def test_base_image_enum(self):
        """Test BaseImage enum values."""
        assert BaseImage.BASE.value == "base"
        assert BaseImage.GOLANG.value == "golang"
        assert BaseImage.DOTNET.value == "dotnet"

        # Test from string
        assert BaseImage("base") == BaseImage.BASE
        assert BaseImage("golang") == BaseImage.GOLANG
