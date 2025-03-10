"""
Tests for file reading and writing operations in code_assistant.
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
import code_assistant
from pathlib import Path


class TestFileIO:
    """Tests for file reading and writing operations."""
    
    def setup_method(self):
        """Set up temporary directory and test files for file IO tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_working_dir = code_assistant.WORKING_DIRECTORY
        
        # Create test file with content
        self.test_file_path = os.path.join(self.temp_dir.name, "test_file.txt")
        with open(self.test_file_path, 'w', encoding='utf-8') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
    
    def teardown_method(self):
        """Clean up temporary directory and restore original working directory."""
        code_assistant.WORKING_DIRECTORY = self.orig_working_dir
        self.temp_dir.cleanup()
    
    def test_read_file_content_entire_file(self):
        """Test reading an entire file."""
        content = code_assistant.read_file_content(self.test_file_path)
        assert content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
    
    def test_read_file_content_line_range(self):
        """Test reading a specific range of lines."""
        # Read lines 2-4 (1-indexed)
        content = code_assistant.read_file_content(self.test_file_path, start_line=2, end_line=4)
        assert "Line 2\nLine 3\nLine 4" in content
        assert "Line 1" not in content
        assert "Line 5" not in content
        
        # Line info should be included
        assert "Lines 2-4" in content
    
    def test_read_file_content_start_line_only(self):
        """Test reading from a start line to the end."""
        content = code_assistant.read_file_content(self.test_file_path, start_line=3)
        assert "Line 3\nLine 4\nLine 5" in content
        assert "Line 1" not in content
        assert "Line 2" not in content
    
    def test_read_file_content_beyond_file_end(self):
        """Test reading beyond the end of the file."""
        with patch('builtins.print') as mock_print:
            content = code_assistant.read_file_content(self.test_file_path, start_line=1, end_line=10)
            
            # Should print a warning about end line being beyond the file
            warning_printed = any("beyond the end of the file" in str(args) for args, _ in mock_print.call_args_list)
            assert warning_printed, "Should warn when end_line is beyond file length"
            
            # Should still read the entire file
            assert "Line 1\nLine 2\nLine 3\nLine 4\nLine 5" in content
    
    def test_read_file_not_found(self):
        """Test handling of file not found."""
        with patch('builtins.print') as mock_print:
            content = code_assistant.read_file_content("nonexistent_file.txt")
            
            # Should return None for file not found
            assert content is None
            
            # Should print an error message
            error_printed = any("not found" in str(args) for args, _ in mock_print.call_args_list)
            assert error_printed, "Should print error when file not found"
    
    def test_read_file_with_working_directory(self):
        """Test reading a file with working directory set."""
        # Set working directory to temp dir
        code_assistant.WORKING_DIRECTORY = self.temp_dir.name
        
        # Test with relative path
        filename = os.path.basename(self.test_file_path)
        content = code_assistant.read_file_content(filename)
        assert content == "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n"
        
        # Test with absolute path outside working directory
        outside_file = tempfile.NamedTemporaryFile(delete=False, mode='w')
        try:
            outside_file.write("Outside working directory")
            outside_file.close()
            
            with patch('builtins.print') as mock_print:
                content = code_assistant.read_file_content(outside_file.name)
                assert content is None
                
                # Should print an error about being outside working directory
                error_printed = any("outside the working directory" in str(args) for args, _ in mock_print.call_args_list)
                assert error_printed, "Should print error when file is outside working directory"
        finally:
            os.unlink(outside_file.name)
    
    @patch('os.access')
    def test_read_file_not_readable(self, mock_access):
        """Test handling file with no read permission."""
        mock_access.return_value = False
        
        with patch('builtins.print') as mock_print:
            content = code_assistant.read_file_content(self.test_file_path)
            
            # Should return None for non-readable file
            assert content is None
            
            # Should print an error message
            error_printed = any("not readable" in str(args) for args, _ in mock_print.call_args_list)
            assert error_printed, "Should print error when file is not readable"
    
    def test_read_file_with_unicode_error(self):
        """Test handling of Unicode decode errors."""
        # Create a binary file that will cause Unicode decode error
        binary_file = os.path.join(self.temp_dir.name, "binary_file.bin")
        with open(binary_file, 'wb') as f:
            f.write(b'\xFF\xFE\x00\x00\xFF')  # Invalid UTF-8
        
        with patch('builtins.print') as mock_print:
            with patch('code_assistant.detect_file_encoding', return_value=('utf-8', False)):
                # This should try to read as UTF-8 but fail and fall back to binary mode
                content = code_assistant.read_file_content(binary_file)
                
                # Should print an error about Unicode decode
                error_printed = any("Failed to decode" in str(args) for args, _ in mock_print.call_args_list)
                assert error_printed, "Should print error when Unicode decode fails"
                
                # Should attempt binary fallback
                fallback_printed = any("binary fallback" in str(args) for args, _ in mock_print.call_args_list)
                assert fallback_printed, "Should print message about binary fallback"
                
                # Should return content using fallback encoding
                assert content is not None
    
    def test_write_file_content(self):
        """Test writing content to a file."""
        output_file = os.path.join(self.temp_dir.name, "output.txt")
        content = "Test output content"
        
        result = code_assistant.write_file_content(output_file, content)
        assert result is True, "Write operation should succeed"
        
        # Verify the content was written correctly
        with open(output_file, 'r', encoding='utf-8') as f:
            written_content = f.read()
        assert written_content == content
    
    def test_write_file_content_with_backup(self):
        """Test writing to an existing file with backup."""
        # First write initial content
        output_file = os.path.join(self.temp_dir.name, "existing.txt")
        initial_content = "Initial content"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        
        # Now write new content with backup
        new_content = "New content"
        with patch('builtins.print') as mock_print:
            result = code_assistant.write_file_content(output_file, new_content, create_backup=True)
            assert result is True, "Write operation should succeed"
            
            # Check backup message
            backup_msg = any("Created backup" in str(args) for args, _ in mock_print.call_args_list)
            assert backup_msg, "Should print message about backup creation"
        
        # Verify backup file exists and has original content
        backup_file = f"{output_file}.bak"
        assert os.path.exists(backup_file), "Backup file should exist"
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_content = f.read()
        assert backup_content == initial_content
        
        # Verify the new content was written
        with open(output_file, 'r', encoding='utf-8') as f:
            written_content = f.read()
        assert written_content == new_content
    
    def test_write_file_content_creates_directories(self):
        """Test writing to a file in a new directory structure."""
        new_dir = os.path.join(self.temp_dir.name, "new_dir", "subdir")
        output_file = os.path.join(new_dir, "output.txt")
        content = "Content in new directory"
        
        with patch('builtins.print') as mock_print:
            result = code_assistant.write_file_content(output_file, content)
            assert result is True, "Write operation should succeed"
            
            # Check directory creation message
            dir_created_msg = any("Created directory" in str(args) for args, _ in mock_print.call_args_list)
            assert dir_created_msg, "Should print message about directory creation"
        
        # Verify the directory was created
        assert os.path.exists(new_dir), "Directory structure should be created"
        
        # Verify the content was written correctly
        with open(output_file, 'r', encoding='utf-8') as f:
            written_content = f.read()
        assert written_content == content
    
    def test_write_file_with_working_directory(self):
        """Test writing a file with working directory set."""
        # Set working directory to temp dir
        code_assistant.WORKING_DIRECTORY = self.temp_dir.name
        
        # Test with relative path
        relative_path = "output_in_working_dir.txt"
        content = "Content in working directory"
        
        result = code_assistant.write_file_content(relative_path, content)
        assert result is True, "Write operation should succeed"
        
        # Verify the file was created in the working directory
        full_path = os.path.join(self.temp_dir.name, relative_path)
        assert os.path.exists(full_path), "File should be created in working directory"
        
        # Test with absolute path outside working directory
        outside_dir = tempfile.TemporaryDirectory()
        try:
            outside_path = os.path.join(outside_dir.name, "outside.txt")
            
            with patch('builtins.print') as mock_print:
                result = code_assistant.write_file_content(outside_path, "Outside content")
                assert result is False, "Write should fail for path outside working directory"
                
                # Should print an error about being outside working directory
                error_printed = any("outside the working directory" in str(args) for args, _ in mock_print.call_args_list)
                assert error_printed, "Should print error when file is outside working directory"
        finally:
            outside_dir.cleanup()
    
    @patch('builtins.open')
    def test_write_file_error(self, mock_open):
        """Test handling of write errors."""
        mock_open.side_effect = PermissionError("Permission denied")
        
        with patch('builtins.print') as mock_print:
            result = code_assistant.write_file_content("test.txt", "Content")
            assert result is False, "Write should fail on permission error"
            
            # Should print an error message
            error_printed = any("Error writing" in str(args) for args, _ in mock_print.call_args_list)
            assert error_printed, "Should print error when write fails"
    
    def test_generate_colored_diff(self):
        """Test generating colored diff between original and modified content."""
        original = "Line 1\nLine 2\nLine 3"
        modified = "Line 1\nLine 2 modified\nLine 3\nLine 4"
        
        diff = code_assistant.generate_colored_diff(original, modified, "test.txt")
        
        # Check that diff contains expected content
        assert "Line 2 modified" in diff
        assert "Line 4" in diff
        
        # Check that diff formatting is applied (we can't check colors directly)
        assert "+" in diff  # Added lines
        assert "-" in diff  # Removed lines 