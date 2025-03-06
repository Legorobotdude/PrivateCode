"""
Tests for command execution functionality in the code assistant.
"""
import pytest
from unittest.mock import patch, MagicMock
import subprocess
import code_assistant

class TestCommandExecution:
    """Tests for the command execution functionality."""
    
    def test_is_safe_command(self):
        """Test the is_safe_command function."""
        # Test safe commands
        safe, _ = code_assistant.is_safe_command("python -m pytest")
        assert safe, "Python commands should be safe"
        
        safe, _ = code_assistant.is_safe_command("ls -la")
        assert safe, "ls commands should be safe"
        
        safe, _ = code_assistant.is_safe_command("git status")
        assert safe, "git status should be safe"
        
        # Test unsafe commands
        safe, message = code_assistant.is_safe_command("rm -rf /")
        assert not safe, "rm -rf / should be unsafe"
        assert "dangerous operation" in message.lower(), "Error message should mention dangerous operation"
        
        safe, message = code_assistant.is_safe_command("sudo apt-get install something")
        assert not safe, "sudo commands should be unsafe"
        assert "dangerous operation" in message.lower(), "Error message should mention dangerous operation"
        
        safe, message = code_assistant.is_safe_command("echo 'test' > file.txt")
        assert not safe, "commands with > redirection should be unsafe"
        assert "dangerous operation" in message.lower(), "Error message should mention dangerous operation"
        
        # Test edge cases
        safe, _ = code_assistant.is_safe_command("python; rm -rf /")
        assert not safe, "Command injection should be unsafe"
        
        safe, _ = code_assistant.is_safe_command("git commit -m 'fix' && chmod 777 *")
        assert not safe, "Multiple commands with unsafe parts should be unsafe"
    
    @patch('subprocess.run')
    def test_execute_command(self, mock_run):
        """Test the execute_command function."""
        # Mock a successful command execution
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Command output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        output = code_assistant.execute_command("echo 'test'")
        assert "Command output" in output, "Output should contain command result"
        assert "Exit Code: 0" in output, "Output should contain exit code"
        
        # Mock a failed command execution
        mock_result.returncode = 1
        mock_result.stderr = "Command error"
        output = code_assistant.execute_command("invalid_command")
        assert "Command error" in output, "Output should contain error message"
        assert "Exit Code: 1" in output, "Output should contain exit code"
        
        # Test with subprocess raising an exception
        mock_run.side_effect = subprocess.SubprocessError("Process error")
        output = code_assistant.execute_command("problematic_command")
        assert "error" in output.lower(), "Output should mention error"
    
    def test_extract_specific_command(self):
        """Test the extract_specific_command function."""
        # Test with a command in single quotes
        query = "run: 'python script.py'"
        command = code_assistant.extract_specific_command(query)
        assert command == "python script.py", f"Expected 'python script.py', got '{command}'"
        
        # Test with quotes and spaces
        query = "run: 'echo \"Hello World\"'"
        command = code_assistant.extract_specific_command(query)
        assert command == "echo \"Hello World\"", f"Expected \"echo \\\"Hello World\\\"\", got '{command}'"
        
        # Test with special characters
        query = "run: 'grep -r \"pattern\" .'"
        command = code_assistant.extract_specific_command(query)
        assert command == "grep -r \"pattern\" .", f"Expected \"grep -r \\\"pattern\\\" .\", got '{command}'"
        
        # Test with no command in quotes
        query = "Just a regular query"
        command = code_assistant.extract_specific_command(query)
        assert command is None, f"Expected None, got '{command}'" 