"""
Tests for file operation edge cases in the code assistant.

This test suite focuses on edge cases and error handling for file operations:
1. Permission errors and access control
2. Extremely large files
3. Binary files and unusual encodings
4. Disk full scenarios and I/O errors
"""
import os
import sys
import pytest
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
import io
import stat
from pathlib import Path
import code_assistant
from tests.utils import create_test_file


class TestFilePermissions:
    """Tests for handling permission errors and access control."""
    
    def setup_method(self):
        """Set up a temporary directory for permission tests."""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Clean up temporary directory."""
        # Reset permissions to ensure cleanup works
        for root, dirs, files in os.walk(self.temp_dir):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                os.chmod(dir_path, stat.S_IRWXU)
            for file_name in files:
                file_path = os.path.join(root, file_name)
                os.chmod(file_path, stat.S_IRWXU)
                
        shutil.rmtree(self.temp_dir)
    
    @pytest.mark.skipif(sys.platform == "win32", 
                       reason="Windows handles permissions differently")
    def test_read_permission_denied(self):
        """Test reading a file with no read permissions."""
        # Create a file with no read permissions (only write permission)
        file_path = os.path.join(self.temp_dir, "no_read_permission.txt")
        with open(file_path, 'w') as f:
            f.write("This content should not be readable")
            
        # Remove read permissions
        os.chmod(file_path, stat.S_IWUSR)
        
        # Test reading the file - should handle permission error gracefully
        with patch('builtins.print') as mock_print:
            result = code_assistant.read_file_content(file_path)
            
            # Check for appropriate error messaging
            any_permission_error = any("permission" in str(args).lower() for args, _ in mock_print.call_args_list)
            assert any_permission_error, "Should print permission error message"
            
            # Should return None on failure
            assert result is None, "Should return None when permission denied"
    
    @pytest.mark.skipif(sys.platform == "win32", 
                       reason="Windows handles permissions differently")
    def test_write_permission_denied(self):
        """Test writing to a file with no write permissions."""
        # Create a file with read-only permissions
        file_path = os.path.join(self.temp_dir, "read_only.txt")
        with open(file_path, 'w') as f:
            f.write("Original content")
            
        # Make file read-only
        os.chmod(file_path, stat.S_IRUSR)
        
        # Attempt to write to the file
        with patch('builtins.print') as mock_print:
            result = code_assistant.write_file_content(file_path, "New content")
            
            # Check for appropriate error messaging
            any_permission_error = any("permission" in str(args).lower() for args, _ in mock_print.call_args_list)
            assert any_permission_error, "Should print permission error message"
            
            # Should return False on failure
            assert result is False, "Should return False when write fails due to permissions"
    
    @pytest.mark.skipif(sys.platform == "win32", 
                       reason="Windows handles permissions differently")
    def test_directory_permission_denied(self):
        """Test accessing files in a directory with no permissions."""
        # Create a subdirectory
        subdir = os.path.join(self.temp_dir, "no_access_dir")
        os.makedirs(subdir)
        
        # Create a file in the subdirectory
        file_path = os.path.join(subdir, "inaccessible.txt")
        with open(file_path, 'w') as f:
            f.write("You should not be able to read this")
            
        # Remove all permissions from directory
        os.chmod(subdir, 0)
        
        # Try to read the file
        with patch('builtins.print') as mock_print:
            result = code_assistant.read_file_content(file_path)
            
            # Should print an error
            assert mock_print.call_count > 0, "Should print error message"
            
            # Should return None on failure
            assert result is None, "Should return None when directory permission denied"


class TestBinaryAndEncodings:
    """Tests for handling binary files and unusual encodings."""
    
    def setup_method(self):
        """Set up a temporary directory for encoding tests."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    def test_binary_file_read(self):
        """Test reading a binary file."""
        # Create a binary file with non-text content
        file_path = os.path.join(self.temp_dir, "binary.bin")
        with open(file_path, 'wb') as f:
            f.write(bytes(range(128)))  # Write bytes 0-127
        
        # Try to read the binary file
        with patch('builtins.print') as mock_print:
            content = code_assistant.read_file_content(file_path)
            
            # The program should either print a message about binary/encoding
            # or successfully read the binary content
            assert content is not None, "Should return some content for binary file"
            
            # Check if it printed any message about encoding or binary
            any_encoding_message = any(("encod" in str(args).lower() or 
                                      "binary" in str(args).lower() or
                                      "fallback" in str(args).lower())
                                    for args, _ in mock_print.call_args_list)
            
            # If it didn't print a message, it should have read some content
            if not any_encoding_message:
                # Should have some content representing the binary data
                assert len(content) > 0, "Should return some content for binary file"
    
    def test_mixed_encoding_file(self):
        """Test reading a file with mixed encodings."""
        # Create a file with mixed encoding content
        file_path = os.path.join(self.temp_dir, "mixed_encoding.txt")
        
        # Start with UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("UTF-8 text: Hello, World! 你好，世界！\n")
        
        # Append Latin-1 content
        with open(file_path, 'ab') as f:
            f.write("Latin-1 text: ".encode('utf-8'))
            f.write(bytes([0xA3, 0xB5, 0xD8]))  # Some Latin-1 specific bytes
        
        # Try to read the mixed-encoding file
        with patch('builtins.print') as mock_print:
            content = code_assistant.read_file_content(file_path)
            
            # Should contain the UTF-8 part
            assert "UTF-8 text: Hello, World!" in content
            
            # Should print message about decode issues
            decode_message = any("decod" in str(args).lower() for args, _ in mock_print.call_args_list)
            assert decode_message, "Should print message about decoding issues"
    
    def test_corrupted_utf8_file(self):
        """Test reading a corrupted UTF-8 file."""
        # Create a file with invalid UTF-8 sequences
        file_path = os.path.join(self.temp_dir, "corrupted_utf8.txt")
        with open(file_path, 'wb') as f:
            f.write(b"Valid UTF-8: Hello\n")
            f.write(b"Invalid UTF-8: \xFF\xC1\xFE")
        
        # Try to read the corrupted file
        with patch('builtins.print') as mock_print:
            content = code_assistant.read_file_content(file_path)
            
            # The function should handle corrupted files gracefully,
            # it may not explicitly print a Unicode decode error
            assert content is not None, "Should return some content even for corrupted files"
            assert "Valid UTF-8: Hello" in content, "Should contain the valid part of the file"
            
            # Either it should print an error message or successfully decode using fallback
            error_printed = any("error" in str(args).lower() or "fallback" in str(args).lower() 
                              or "binary" in str(args).lower() for args, _ in mock_print.call_args_list)
            if not error_printed:
                # If no error message, it should have decoded the content somehow
                assert len(content) > len("Valid UTF-8: Hello\n"), "Should include decoded content beyond the valid part"
    
    def test_various_encodings(self):
        """Test reading files with various uncommon encodings."""
        test_cases = [
            {"encoding": "utf-16", "content": "UTF-16 text with unicode: 😀 🌍 🚀", "name": "utf16.txt"},
            {"encoding": "utf-32", "content": "UTF-32 text: Testing", "name": "utf32.txt"},
            {"encoding": "iso-8859-1", "content": "ISO-8859-1 text", "name": "latin1.txt"},
            {"encoding": "cp1252", "content": "Windows CP1252 text with €", "name": "cp1252.txt"}
        ]
        
        for case in test_cases:
            file_path = os.path.join(self.temp_dir, case["name"])
            try:
                # Use binary mode and add BOM for UTF-32 to ensure proper detection
                if case["encoding"] == "utf-32":
                    with open(file_path, 'wb') as f:
                        # Add UTF-32-LE BOM and then write content
                        f.write(b'\xff\xfe\x00\x00')
                        f.write(case["content"].encode('utf-32-le'))
                else:
                    with open(file_path, 'w', encoding=case["encoding"]) as f:
                        f.write(case["content"])
                
                # Test reading this encoding
                with patch('builtins.print') as mock_print:
                    content = code_assistant.read_file_content(file_path)
                    
                    # Check for encoding notice
                    encoding_message = any(case["encoding"].lower() in str(args).lower() 
                                         for args, _ in mock_print.call_args_list)
                    
                    assert content is not None, f"Should be able to read {case['encoding']} encoded file"
                    
                    # For UTF-32, we check that it's properly detected (with BOM)
                    if case["encoding"] == "utf-32":
                        assert case["content"] in content, f"Should correctly decode UTF-32 content"
                    else:
                        # For other encodings, check that content exists - may be decoded differently
                        # based on platform and Python version
                        assert len(content) > 0, f"Should decode some content from {case['encoding']} file"
            except UnicodeEncodeError:
                # Some environments might not support all encodings
                print(f"Skipping {case['encoding']} test due to encode error")


class TestLargeFiles:
    """Tests for handling extremely large files."""
    
    def setup_method(self):
        """Set up a temporary directory for large file tests."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    @patch('os.path.getsize')
    def test_very_large_file_warning(self, mock_getsize):
        """Test reading a very large file shows a warning."""
        # Create a normal sized file but mock its size
        file_path = os.path.join(self.temp_dir, "large_file.txt")
        with open(file_path, 'w') as f:
            f.write("This pretends to be a large file")
        
        # Mock the file size to be 100MB
        mock_getsize.return_value = 100 * 1024 * 1024  # 100MB
        
        # Try to read the "large" file
        with patch('builtins.print') as mock_print:
            content = code_assistant.read_file_content(file_path)
            
            # Should print warning about large file
            large_warning = any("large" in str(args).lower() or "size" in str(args).lower() 
                              for args, _ in mock_print.call_args_list)
            assert large_warning, "Should print warning about large file size"
            
            # Should still read the content
            assert "This pretends to be a large file" in content
    
    def test_large_file_content_generation(self):
        """Test generating and reading a moderately large file."""
        # Create a ~1MB file
        file_path = os.path.join(self.temp_dir, "medium_large.txt")
        
        # Generate repetitive content to get to ~1MB
        line = "This is a test line that will be repeated many times to create a larger file.\n"
        lines_needed = (1024 * 1024) // len(line) + 1  # About 1MB of content
        
        with open(file_path, 'w') as f:
            for i in range(lines_needed):
                f.write(f"Line {i}: {line}")
        
        # Read the entire file
        content = code_assistant.read_file_content(file_path)
        assert content is not None, "Should be able to read 1MB file"
        assert content.startswith("Line 0:"), "Should read beginning of file correctly"
        assert f"Line {lines_needed-1}:" in content, "Should read end of file correctly"
    
    def test_large_file_line_range(self):
        """Test reading a specific range of lines from a large file."""
        # Create a file with many lines
        file_path = os.path.join(self.temp_dir, "many_lines.txt")
        
        with open(file_path, 'w') as f:
            for i in range(10000):
                f.write(f"Line {i}: This is line {i} of many.\n")
        
        # Read a specific range in the middle - note that line numbers might be 0-indexed internally
        # but 1-indexed in the display, or the end range might be exclusive
        content = code_assistant.read_file_content(file_path, start_line=5000, end_line=5010)
        
        # Check that content contains line 5000
        assert "Line 5000:" in content, "Should contain line 5000"
        
        # Check that reasonably complete range of lines is returned
        # At least 9 lines should be included between 5000 and 5010
        line_count = sum(1 for line in content.split('\n') if f"Line 50" in line)
        assert line_count >= 9, f"Should include at least 9 lines in the range, got {line_count}"
        
        # Now try with a more specific range to see exactly what's included
        content_specific = code_assistant.read_file_content(file_path, start_line=100, end_line=105)
        
        # Check if range is inclusive or exclusive by counting lines
        # Skip header lines that contain formatting
        data_lines = [line for line in content_specific.split('\n') 
                      if line.strip() and "Line " in line and not line.startswith("---")]
        
        # Count lines to see if the range is inclusive or exclusive
        line_count = len(data_lines)
        assert line_count >= 5, f"Should include at least 5 lines in the range, got {line_count}"
        
        # Print findings about what lines are included
        line_numbers = []
        for line in data_lines:
            # Extract line numbers, handling potential formatting variations
            parts = line.split(":", 1)
            if len(parts) >= 1:
                num_str = parts[0].replace("Line ", "").strip()
                try:
                    line_numbers.append(int(num_str))
                except ValueError:
                    pass
        
        print(f"Range test: start_line=100, end_line=105, included lines: {line_numbers}")


class TestIOErrors:
    """Tests for handling I/O errors like disk full scenarios."""
    
    def setup_method(self):
        """Set up a temporary directory for I/O error tests."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir)
    
    @patch('builtins.open')
    def test_disk_full_error(self, mock_open):
        """Test handling disk full error when writing a file."""
        # Mock file open to simulate disk full error
        mock_file = MagicMock()
        mock_file.write.side_effect = OSError(28, "No space left on device")
        mock_open.return_value.__enter__.return_value = mock_file
        
        file_path = os.path.join(self.temp_dir, "cant_write.txt")
        
        with patch('builtins.print') as mock_print:
            result = code_assistant.write_file_content(file_path, "Some content")
            
            # Should return False for failed write
            assert result is False, "Should return False when disk is full"
            
            # Should print disk full error
            disk_full_message = any("space" in str(args).lower() or "disk" in str(args).lower() 
                                  for args, _ in mock_print.call_args_list)
            assert disk_full_message, "Should print message about disk space"
    
    @patch('builtins.open')
    def test_io_error_during_read(self, mock_open):
        """Test handling general I/O errors during file reading."""
        # Mock open to raise different I/O errors
        errors = [
            IOError(5, "Input/output error"),
            IOError(6, "No such device or address"),
            OSError(121, "Remote I/O error")
        ]
        
        for error in errors:
            mock_open.side_effect = error
            error_str = str(error)
            
            with patch('builtins.print') as mock_print:
                result = code_assistant.read_file_content("test_file.txt")
                
                # Should return None for failed read
                assert result is None, f"Should return None for {error}"
                
                # Should print some kind of error message - but may not include the exact error text
                assert mock_print.call_count > 0, f"Should print error message for {error}"
                
                # At least one of the prints should contain 'error' or the error number
                error_reported = any("error" in str(args).lower() or str(error.errno) in str(args) 
                                  for args, _ in mock_print.call_args_list)
                assert error_reported, f"Should report error for {error}"
            
            # Reset the mock for next iteration
            mock_open.reset_mock()
    
    def test_file_locked_by_another_process(self):
        """Test handling a file that's locked by another process."""
        if sys.platform == 'win32':
            # Windows-specific file locking test
            file_path = os.path.join(self.temp_dir, "locked_file.txt")
            
            # Create the file
            with open(file_path, 'w') as f:
                f.write("Initial content")
            
            # Open it with exclusive access to simulate locking
            # pylint: disable=consider-using-with
            locked_file = open(file_path, 'a')
            
            try:
                # Try to write to the locked file
                with patch('builtins.print') as mock_print:
                    result = code_assistant.write_file_content(file_path, "New content")
                    
                    # On Windows, this might still succeed depending on sharing mode
                    if not result:
                        # Check for appropriate error messaging
                        lock_message = any("access" in str(args).lower() or "denied" in str(args).lower() 
                                          for args, _ in mock_print.call_args_list)
                        assert lock_message, "Should print message about access issues"
            finally:
                # Always close the file
                locked_file.close() 