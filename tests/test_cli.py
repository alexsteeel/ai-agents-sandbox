"""Integration tests for AI Agents Sandbox CLI."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
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
        assert "docker" in result.output
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
            result = self.runner.invoke(cli, ["init", "."])
            
            # Should succeed or show Docker message
            assert "Project initialization complete" in result.output or "Docker" in result.output
    
    @patch("ai_sbx.commands.init.ensure_group_exists")
    @patch("ai_sbx.commands.init.add_user_to_group")
    def test_init_global(self, mock_add_user, mock_ensure_group):
        """Test global initialization."""
        mock_ensure_group.return_value = True
        mock_add_user.return_value = True
        
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["init", "--global"], input="n\n")
            
            # Should show configuration
            assert "Global" in result.output or "configuration" in result.output


class TestDockerCommand:
    """Test docker commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch("ai_sbx.commands.docker.is_docker_running")
    def test_docker_build_requires_docker(self, mock_docker):
        """Test docker build requires Docker."""
        mock_docker.return_value = False
        
        result = self.runner.invoke(cli, ["docker", "build"])
        assert result.exit_code != 0
        assert "Docker is not running" in result.output
    
    @patch("ai_sbx.commands.docker.is_docker_running")
    @patch("ai_sbx.commands.docker._build_image")
    def test_docker_build_variants(self, mock_build, mock_docker):
        """Test building Docker image variants."""
        mock_docker.return_value = True
        mock_build.return_value = True
        
        result = self.runner.invoke(cli, ["docker", "build", "--variant", "python"])
        
        # Should attempt to build
        assert mock_build.called or "Building" in result.output
    
    @patch("ai_sbx.commands.docker.find_project_root")
    def test_docker_up_requires_project(self, mock_find_root):
        """Test docker up requires project."""
        mock_find_root.return_value = None
        
        result = self.runner.invoke(cli, ["docker", "up"])
        assert result.exit_code != 0
        assert "Not in a project" in result.output
    
    @patch("ai_sbx.commands.docker.find_project_root")
    @patch("ai_sbx.commands.docker.run_command")
    def test_docker_ps(self, mock_run, mock_find_root):
        """Test docker ps command."""
        mock_find_root.return_value = Path("/test/project")
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"Names": "test-devcontainer", "Image": "ai-sbx/base", "State": "running"}'
        )
        
        result = self.runner.invoke(cli, ["docker", "ps"])
        
        # Should show containers or no containers message
        assert "Containers" in result.output or "No running containers" in result.output


class TestWorktreeCommand:
    """Test worktree commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    @patch("ai_sbx.commands.worktree.find_project_root")
    def test_worktree_create_requires_git(self, mock_find_root):
        """Test worktree create requires git repository."""
        mock_find_root.return_value = None
        
        result = self.runner.invoke(cli, ["worktree", "create", "test task"])
        assert result.exit_code == 0
        assert "Not in a git repository" in result.output
    
    @patch("ai_sbx.commands.worktree._list_worktrees")
    def test_worktree_list(self, mock_list):
        """Test worktree list command."""
        mock_list.return_value = [
            {
                "path": "/test/worktree",
                "branch": "test-branch",
                "commit": "abc123",
            }
        ]
        
        result = self.runner.invoke(cli, ["worktree", "list"])
        assert result.exit_code == 0
        assert "worktree" in result.output or "Worktrees" in result.output
    
    @patch("ai_sbx.commands.worktree._list_worktrees")
    def test_worktree_remove_interactive(self, mock_list):
        """Test worktree remove interactive mode."""
        mock_list.return_value = []
        
        result = self.runner.invoke(cli, ["worktree", "remove"])
        assert result.exit_code == 0
        assert "No worktrees found" in result.output


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
            notifications_dir = temp_path / ".ai_agents_sandbox" / "notifications"
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