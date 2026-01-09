"""Tests for template generation module."""

import tempfile
from pathlib import Path

from ai_sbx.config import IDE, BaseImage, ProjectConfig
from ai_sbx.templates import TemplateManager


class TestTemplateManager:
    """Test template manager."""

    def test_init_default(self):
        """Test template manager initialization with defaults."""
        manager = TemplateManager()
        assert manager.templates_dir is not None

    def test_init_custom_dir(self):
        """Test template manager initialization with custom directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            custom_dir = Path(temp_dir)
            manager = TemplateManager(templates_dir=custom_dir)
            assert manager.templates_dir == custom_dir

    def test_generate_project_files(self):
        """Test generating project files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / ".devcontainer"
            output_dir.mkdir(parents=True)
            config = ProjectConfig(
                name="test-project",
                path=Path(temp_dir),
                preferred_ide=IDE.VSCODE,
                base_image=BaseImage.BASE,
            )

            manager = TemplateManager()
            success = manager.generate_project_files(output_dir, config)

            assert success is True
            # Check files were created
            assert (output_dir / "devcontainer.json").exists()
            assert (output_dir / "Dockerfile").exists()
            assert (output_dir / ".env").exists()

    def test_generate_files_requires_directory(self):
        """Test that generate_project_files requires existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / ".devcontainer"
            # Don't create directory
            config = ProjectConfig(
                name="test-project",
                path=Path(temp_dir),
            )

            manager = TemplateManager()
            # Should fail because directory doesn't exist
            success = manager.generate_project_files(output_dir, config)

            # Now create directory and try again
            output_dir.mkdir(parents=True)
            success = manager.generate_project_files(output_dir, config)
            assert success is True

    def test_generate_actual_files(self):
        """Test generating actual files without mocking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / ".devcontainer"
            output_dir.mkdir(parents=True)  # Create directory first
            config = ProjectConfig(
                name="test-project",
                path=Path(temp_dir),
                preferred_ide=IDE.PYCHARM,
                base_image=BaseImage.DOTNET,
            )

            manager = TemplateManager()
            success = manager.generate_project_files(output_dir, config)

            # Check that files were created
            assert success is True
            assert (output_dir / "devcontainer.json").exists()
            assert (output_dir / "Dockerfile").exists()
            assert (output_dir / ".env").exists()
            assert (output_dir / ".gitignore").exists()
            assert (output_dir / "docker-compose.override.yaml").exists()
            assert (output_dir / "init.sh").exists()
            assert (output_dir / "ai-sbx.yaml.template").exists()

            # Check init script is executable
            init_script = output_dir / "init.sh"
            assert init_script.stat().st_mode & 0o111  # Check executable bit

            # Check some content
            env_content = (output_dir / ".env").read_text()
            # PROJECT_NAME uses the directory name (config.path.name), not config.name
            assert "PROJECT_NAME=" in env_content
            assert "COMPOSE_PROJECT_NAME=" in env_content

            dockerfile_content = (output_dir / "Dockerfile").read_text()
            assert "FROM ai-agents-sandbox/devcontainer-dotnet:1.0.0" in dockerfile_content

    def test_force_overwrite(self):
        """Test force overwrite existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / ".devcontainer"
            output_dir.mkdir(parents=True)

            # Create existing file with different content
            existing_file = output_dir / ".env"
            existing_file.write_text("OLD_CONTENT=test")

            config = ProjectConfig(
                name="new-project",
                path=Path(temp_dir),
            )

            manager = TemplateManager()

            # Without force, should not overwrite
            success = manager.generate_project_files(output_dir, config, force=False)
            content = existing_file.read_text()
            assert "OLD_CONTENT=test" in content

            # With force, should overwrite
            success = manager.generate_project_files(output_dir, config, force=True)
            content = existing_file.read_text()
            # PROJECT_NAME uses directory name, not config.name
            assert "PROJECT_NAME=" in content
            assert "OLD_CONTENT" not in content

    def test_handles_invalid_config(self):
        """Test handling of invalid configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / ".devcontainer"
            output_dir.mkdir(parents=True)  # Create directory first

            # Config with invalid characters in name
            config = ProjectConfig(
                name="test/project:invalid",
                path=Path(temp_dir),
            )

            manager = TemplateManager()
            # Should still generate files, sanitizing the name
            success = manager.generate_project_files(output_dir, config)
            assert success is True
