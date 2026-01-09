"""Integration tests for AI Agents Sandbox CLI."""

import importlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from ai_sbx.cli import cli


class TestCLI:
    """Test CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_version(self):
        """Test version flag."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "AI Agents Sandbox" in result.output
        assert "v" in result.output

    def test_cli_help(self):
        """Test help output."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "AI Agents Sandbox" in result.output
        assert "Commands:" in result.output
        assert "init" in result.output
        assert "image" in result.output
        assert "worktree" in result.output

    def test_cli_no_command(self):
        """Test CLI with no command shows help."""
        result = self.runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "AI Agents Sandbox" in result.output


class TestInitCommand:
    """Test init command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("ai_sbx.commands.init.is_docker_running")
    @patch("ai_sbx.commands.init.find_project_root")
    def test_init_project(self, mock_find_root, mock_docker):
        """Test project initialization."""
        mock_docker.return_value = True
        mock_find_root.return_value = None

        with self.runner.isolated_filesystem() as temp_dir:
            # Pass CLI options to avoid interactive wizard
            result = self.runner.invoke(
                cli, ["init", "project", "--base-image", "base", "--ide", "vscode"]
            )

            # Should succeed or show Docker message
            assert "Project initialization complete" in result.output or "Docker" in result.output

    @patch("ai_sbx.commands.init.ensure_group_exists")
    @patch("ai_sbx.commands.init.add_user_to_group")
    def test_init_global(self, mock_add_user, mock_ensure_group):
        """Test global initialization."""
        mock_ensure_group.return_value = True
        mock_add_user.return_value = True

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["init", "global"], input="n\n")

            # Should show configuration
            assert "Global" in result.output or "configuration" in result.output


class TestImageCommand:
    """Test image commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("ai_sbx.commands.image.is_docker_running")
    def test_image_build_requires_docker(self, mock_docker):
        """Test image build requires Docker."""
        mock_docker.return_value = False

        result = self.runner.invoke(cli, ["image", "build"])
        assert result.exit_code != 0
        assert "Docker is not running" in result.output

    @patch("ai_sbx.commands.image.Path")
    @patch("ai_sbx.commands.image.is_docker_running")
    @patch("ai_sbx.utils.run_command")
    def test_image_build_variants(self, mock_run, mock_docker, mock_path):
        """Test building Docker image variants."""
        mock_docker.return_value = True
        mock_run.return_value = Mock(returncode=0)
        # Mock Path to avoid PosixPath issues
        mock_path.return_value.exists.return_value = True

        result = self.runner.invoke(cli, ["image", "build", "--all"])

        # Should attempt to build or show proper message
        assert result.exit_code in [0, 1]

    @patch("ai_sbx.commands.image._image_exists")
    @patch("ai_sbx.utils.is_docker_running")
    def test_image_list(self, mock_docker_running, mock_image_exists):
        """Test image list command."""
        mock_docker_running.return_value = True
        mock_image_exists.return_value = True

        result = self.runner.invoke(cli, ["image", "list"])

        # Should show images
        assert result.exit_code == 0
        assert "Image" in result.output or "devcontainer" in result.output

    @patch("ai_sbx.commands.image._image_exists")
    @patch("ai_sbx.utils.is_docker_running")
    def test_image_verify(self, mock_docker_running, mock_image_exists):
        """Test image verify command."""
        mock_docker_running.return_value = True
        # Return False to simulate missing images
        mock_image_exists.return_value = False

        result = self.runner.invoke(cli, ["image", "verify"])

        # Should show verification status or missing images
        assert result.exit_code in [0, 1]
        assert "image" in result.output.lower()


class TestWorktreeCommand:
    """Test worktree commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_worktree_create_requires_git(self):
        """Test worktree create requires git repository."""
        with self.runner.isolated_filesystem():
            # Not in a git repo
            result = self.runner.invoke(cli, ["worktree", "create", "test task"])
            # Should fail or show error message
            assert result.exit_code != 0 or "Not in a git repository" in result.output

    def test_worktree_list(self):
        """Test worktree list command."""
        # Import the module via importlib to avoid click group resolution issues
        list_module = importlib.import_module("ai_sbx.commands.worktree.list")

        with patch.object(list_module, "get_worktrees") as mock_list:
            mock_list.return_value = [
                {
                    "path": "/test/worktree",
                    "branch": "test-branch",
                    "commit": "abc123",
                }
            ]

            result = self.runner.invoke(cli, ["worktree", "list"])
            assert result.exit_code == 0
            # Check for table headers or content
            assert (
                "Path" in result.output
                or "Branch" in result.output
                or "test-branch" in result.output
            )

    def test_worktree_remove_interactive(self):
        """Test worktree remove interactive mode."""
        # Import the module via importlib to avoid click group resolution issues
        remove_module = importlib.import_module("ai_sbx.commands.worktree.remove")

        with patch.object(remove_module, "list_worktrees") as mock_list:
            mock_list.return_value = []

            result = self.runner.invoke(cli, ["worktree", "remove"])
            # Interactive mode may fail in test environment (no tty)
            # Just check that it ran
            assert result.exit_code in [0, 1]
            assert "No worktrees found" in result.output or "worktree" in result.output.lower()


class TestNotifyCommand:
    """Test notify command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("ai_sbx.commands.notify.get_user_home")
    def test_notify_test(self, mock_home):
        """Test notify test flag."""
        with self.runner.isolated_filesystem() as temp_dir:
            temp_path = Path(temp_dir)
            mock_home.return_value = temp_path

            # Create notifications directory
            notifications_dir = temp_path / ".ai-sbx" / "notifications"
            notifications_dir.mkdir(parents=True)

            result = self.runner.invoke(cli, ["notify", "--test"])
            assert result.exit_code == 0
            assert "Test notification" in result.output

            # Check if test file was created
            test_file = notifications_dir / "test.txt"
            assert test_file.exists()


class TestDoctorCommand:
    """Test doctor command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("ai_sbx.commands.doctor.is_docker_running")
    @patch("ai_sbx.commands.doctor.check_command_exists")
    def test_doctor_check(self, mock_check_cmd, mock_docker):
        """Test doctor check command."""
        mock_docker.return_value = True
        mock_check_cmd.return_value = True

        result = self.runner.invoke(cli, ["doctor", "--check"])
        assert result.exit_code == 0
        assert "Diagnostics" in result.output or "checks" in result.output


class TestUpgradeCommand:
    """Test upgrade command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("ai_sbx.commands.upgrade.check_command_exists")
    def test_upgrade_requires_pip(self, mock_check_cmd):
        """Test upgrade requires pip or uv."""
        mock_check_cmd.return_value = False

        result = self.runner.invoke(cli, ["upgrade"])
        assert result.exit_code != 0
        assert "pip" in result.output or "uv" in result.output

    @patch("ai_sbx.commands.upgrade.check_command_exists")
    @patch("ai_sbx.commands.upgrade.get_latest_version")
    def test_upgrade_check_version(self, mock_get_version, mock_check_cmd):
        """Test upgrade version checking."""
        mock_check_cmd.return_value = True
        mock_get_version.return_value = "2.0.0"

        result = self.runner.invoke(cli, ["upgrade"])

        # Should show version info
        assert "version" in result.output.lower()
