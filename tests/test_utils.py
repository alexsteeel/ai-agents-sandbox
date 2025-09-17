"""Tests for utility functions."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_sbx.utils import (
    check_command_exists,
    create_directory,
    detect_ide,
    find_project_root,
    format_size,
    get_current_user,
    get_platform_info,
    get_user_home,
    is_root,
    prompt_yes_no,
    run_command,
)


class TestRunCommand:
    """Test run_command function."""

    def test_run_simple_command(self):
        """Test running a simple command."""
        result = run_command(["echo", "test"])
        assert result.returncode == 0
        assert result.stdout.strip() == "test"

    def test_run_command_with_error(self):
        """Test running a command that fails."""
        with pytest.raises(Exception):
            run_command(["false"], check=True)

    def test_run_command_no_check(self):
        """Test running a command without checking exit code."""
        result = run_command(["false"], check=False)
        assert result.returncode != 0

    @patch("ai_sbx.utils.subprocess.run")
    def test_run_command_with_sudo(self, mock_run):
        """Test running command with sudo."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        with patch("ai_sbx.utils.is_root", return_value=False):
            run_command(["test"], sudo=True)

        # Check sudo was prepended
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "sudo"


class TestSystemChecks:
    """Test system check functions."""

    def test_is_root(self):
        """Test root check."""
        with patch("os.geteuid", return_value=0):
            assert is_root() is True

        with patch("os.geteuid", return_value=1000):
            assert is_root() is False

    def test_check_command_exists(self):
        """Test command existence check."""
        # Common commands that should exist
        assert check_command_exists("ls") is True
        assert check_command_exists("echo") is True

        # Non-existent command
        assert check_command_exists("nonexistent_command_12345") is False

    def test_get_platform_info(self):
        """Test platform information retrieval."""
        info = get_platform_info()

        assert "system" in info
        assert "release" in info
        assert "version" in info
        assert "machine" in info
        assert "python" in info

        # Check values are non-empty
        assert info["system"]
        assert info["python"]


class TestUserFunctions:
    """Test user-related functions."""

    @patch.dict(os.environ, {"USER": "testuser", "SUDO_USER": ""})
    def test_get_current_user_regular(self):
        """Test getting current user without sudo."""
        assert get_current_user() == "testuser"

    @patch.dict(os.environ, {"USER": "root", "SUDO_USER": "testuser"})
    def test_get_current_user_sudo(self):
        """Test getting current user with sudo."""
        assert get_current_user() == "testuser"

    @patch("ai_sbx.utils.get_current_user")
    def test_get_user_home(self, mock_get_user):
        """Test getting user home directory."""
        mock_get_user.return_value = "testuser"
        home = get_user_home()
        assert home == Path("/home/testuser")

        mock_get_user.return_value = "root"
        home = get_user_home()
        assert home == Path.home()


class TestFileOperations:
    """Test file operation functions."""

    def test_create_directory(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / "test" / "nested"

            result = create_directory(test_dir)
            assert result is True
            assert test_dir.exists()
            assert test_dir.is_dir()

    def test_create_directory_exists(self):
        """Test creating directory that already exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)

            result = create_directory(test_dir, exist_ok=True)
            assert result is True

    def test_find_project_root_with_git(self):
        """Test finding project root with .git directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()
            git_dir = project_dir / ".git"
            git_dir.mkdir()

            # Create a subdirectory
            sub_dir = project_dir / "src" / "module"
            sub_dir.mkdir(parents=True)

            # Find from subdirectory
            root = find_project_root(sub_dir)
            assert root == project_dir

    def test_find_project_root_with_devcontainer(self):
        """Test finding project root with .devcontainer directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "project"
            project_dir.mkdir()
            devcontainer_dir = project_dir / ".devcontainer"
            devcontainer_dir.mkdir()

            root = find_project_root(project_dir)
            assert root == project_dir

    def test_find_project_root_not_found(self):
        """Test finding project root when not in a project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = find_project_root(Path(temp_dir))
            assert root is None


class TestIDEDetection:
    """Test IDE detection."""

    @patch("ai_sbx.utils.check_command_exists")
    def test_detect_ide(self, mock_check):
        """Test IDE detection."""

        # Mock VS Code exists
        def check_side_effect(cmd):
            return cmd == "code"

        mock_check.side_effect = check_side_effect

        ides = detect_ide()
        assert "vscode" in ides

        # Mock multiple IDEs
        def check_multi_side_effect(cmd):
            return cmd in ["code", "pycharm"]

        mock_check.side_effect = check_multi_side_effect

        ides = detect_ide()
        assert "vscode" in ides
        # Note: pycharm might not be detected if only "pycharm" is checked
        # and not "pycharm.sh"


class TestFormatting:
    """Test formatting functions."""

    def test_format_size(self):
        """Test size formatting."""
        assert format_size(0) == "0.0B"
        assert format_size(1024) == "1.0KB"
        assert format_size(1024 * 1024) == "1.0MB"
        assert format_size(1024 * 1024 * 1024) == "1.0GB"
        assert format_size(1536) == "1.5KB"
        assert format_size(1024 * 1024 * 1.5) == "1.5MB"


class TestPrompts:
    """Test prompt functions."""

    @patch("builtins.input")
    def test_prompt_yes_no_yes(self, mock_input):
        """Test yes/no prompt with yes answer."""
        mock_input.return_value = "y"
        assert prompt_yes_no("Continue?") is True

        mock_input.return_value = "yes"
        assert prompt_yes_no("Continue?") is True

    @patch("builtins.input")
    def test_prompt_yes_no_no(self, mock_input):
        """Test yes/no prompt with no answer."""
        mock_input.return_value = "n"
        assert prompt_yes_no("Continue?") is False

        mock_input.return_value = "no"
        assert prompt_yes_no("Continue?") is False

    @patch("builtins.input")
    def test_prompt_yes_no_default(self, mock_input):
        """Test yes/no prompt with default value."""
        mock_input.return_value = ""
        assert prompt_yes_no("Continue?", default=True) is True
        assert prompt_yes_no("Continue?", default=False) is False


class TestDockerFunctions:
    """Test Docker-related functions."""

    @patch("ai_sbx.utils.run_command")
    def test_is_docker_running_true(self, mock_run):
        """Test Docker running check when Docker is running."""
        mock_run.return_value = Mock(
            returncode=0, stdout='{"ID": "test", "ServerVersion": "20.10.0"}'
        )

        from ai_sbx.utils import is_docker_running

        assert is_docker_running() is True

    @patch("ai_sbx.utils.run_command")
    def test_is_docker_running_false(self, mock_run):
        """Test Docker running check when Docker is not running."""
        mock_run.return_value = Mock(returncode=1, stdout="")

        from ai_sbx.utils import is_docker_running

        assert is_docker_running() is False
