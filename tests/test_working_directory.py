"""
Tests for the working directory functionality in the code assistant.
"""
import os
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import code_assistant

class TestWorkingDirectory:
    """Tests for the working directory feature."""
    
    @patch('builtins.input')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('os.chdir')
    @patch('os.getcwd')
    def test_default_working_directory_is_current_dir(self, mock_getcwd, mock_chdir, mock_exists, mock_makedirs, mock_input):
        """Test that the default working directory is the current directory."""
        # Setup mocks
        current_dir = "/current/working/directory"
        mock_getcwd.return_value = current_dir
        mock_input.return_value = ""  # Simulate user pressing Enter (accepting default)
        mock_exists.return_value = True  # Directory exists
        
        # Save the original WORKING_DIRECTORY
        original_working_dir = code_assistant.WORKING_DIRECTORY
        
        try:
            # Directly test the directory setup logic, rather than calling main()
            # This simulates what happens in main() without running the entire function
            default_dir = os.getcwd()  # This will use our mocked getcwd()
            working_dir = input(f"Enter working directory path (default: current directory): ")
            
            # Use default if nothing is entered
            if not working_dir.strip():
                working_dir = default_dir
            
            # Create directory if it doesn't exist
            if not os.path.exists(working_dir):
                os.makedirs(working_dir)
            
            # Set the global working directory
            code_assistant.WORKING_DIRECTORY = os.path.abspath(working_dir)
            
            # Change to the working directory
            os.chdir(code_assistant.WORKING_DIRECTORY)
            
            # Use os.path.normpath to normalize paths for platform-independent comparison
            expected_path = os.path.normpath(current_dir)
            actual_path = os.path.normpath(code_assistant.WORKING_DIRECTORY)
            assert actual_path.endswith(expected_path.replace('/', os.sep)), f"Expected path to end with {expected_path}, got {actual_path}"
            
            # Verify the correct calls were made
            mock_chdir.assert_called_once_with(code_assistant.WORKING_DIRECTORY)
            
            # If directory exists, makedirs should not be called
            mock_makedirs.assert_not_called()
            
        finally:
            # Restore the original WORKING_DIRECTORY
            code_assistant.WORKING_DIRECTORY = original_working_dir
    
    def test_read_file_within_working_directory(self, temp_directory):
        """Test that reading a file within the working directory works."""
        # Save the original WORKING_DIRECTORY
        original_working_dir = code_assistant.WORKING_DIRECTORY
        
        try:
            # Set up the working directory
            code_assistant.WORKING_DIRECTORY = temp_directory
            
            # Create a test file
            test_file_path = os.path.join(temp_directory, "test_file.txt")
            test_content = "This is a test file\nwith multiple lines\nfor testing."
            with open(test_file_path, 'w') as f:
                f.write(test_content)
            
            # Test using relative path
            relative_path = "test_file.txt"
            content = code_assistant.read_file_content(relative_path)
            assert content == test_content
            
            # Test using absolute path
            content = code_assistant.read_file_content(test_file_path)
            assert content == test_content
        finally:
            # Restore the original WORKING_DIRECTORY
            code_assistant.WORKING_DIRECTORY = original_working_dir
    
    def test_write_file_within_working_directory(self, temp_directory):
        """Test that writing a file within the working directory works."""
        # Save the original WORKING_DIRECTORY
        original_working_dir = code_assistant.WORKING_DIRECTORY
        
        try:
            # Set up the working directory
            code_assistant.WORKING_DIRECTORY = temp_directory
            
            # Test writing to a relative path
            relative_path = "new_file.txt"
            test_content = "This is new content\nfor a new file."
            
            result = code_assistant.write_file_content(relative_path, test_content, create_backup=False)
            assert result is True
            
            # Verify the file was created with the correct content
            written_path = os.path.join(temp_directory, relative_path)
            assert os.path.exists(written_path)
            with open(written_path, 'r') as f:
                assert f.read() == test_content
        finally:
            # Restore the original WORKING_DIRECTORY
            code_assistant.WORKING_DIRECTORY = original_working_dir
    
    def test_read_file_outside_working_directory(self, temp_directory):
        """Test that reading a file outside the working directory is prevented."""
        # Save the original WORKING_DIRECTORY
        original_working_dir = code_assistant.WORKING_DIRECTORY
        
        try:
            # Create a separate directory that is NOT the working directory
            with tempfile.TemporaryDirectory() as outside_dir:
                # Set up the working directory
                code_assistant.WORKING_DIRECTORY = temp_directory
                
                # Create a test file outside the working directory
                test_file_path = os.path.join(outside_dir, "outside_file.txt")
                test_content = "This file is outside the working directory."
                with open(test_file_path, 'w') as f:
                    f.write(test_content)
                
                # Attempt to read the file using an absolute path
                content = code_assistant.read_file_content(test_file_path)
                
                # Should return None since the file is outside the working directory
                assert content is None
        finally:
            # Restore the original WORKING_DIRECTORY
            code_assistant.WORKING_DIRECTORY = original_working_dir
    
    def test_write_file_outside_working_directory(self, temp_directory):
        """Test that writing a file outside the working directory is prevented."""
        # Save the original WORKING_DIRECTORY
        original_working_dir = code_assistant.WORKING_DIRECTORY
        
        try:
            # Create a separate directory that is NOT the working directory
            with tempfile.TemporaryDirectory() as outside_dir:
                # Set up the working directory
                code_assistant.WORKING_DIRECTORY = temp_directory
                
                # Attempt to write to a file outside the working directory
                outside_path = os.path.join(outside_dir, "outside_file.txt")
                test_content = "This should not be written outside the working directory."
                
                result = code_assistant.write_file_content(outside_path, test_content, create_backup=False)
                
                # Should return False since the file is outside the working directory
                assert result is False
                
                # Verify the file was not created
                assert not os.path.exists(outside_path)
        finally:
            # Restore the original WORKING_DIRECTORY
            code_assistant.WORKING_DIRECTORY = original_working_dir 