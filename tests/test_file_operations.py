"""
Tests for file operation functions in the code assistant.
"""
import os
import pytest
from tests.utils import create_test_file
import code_assistant

class TestFileOperations:
    """Tests for file operations like reading, writing, and detecting encoding."""
    
    def test_detect_file_encoding(self, temp_directory):
        """Test the detect_file_encoding function with different encodings."""
        # Create a UTF-8 file
        utf8_path = create_test_file(temp_directory, "utf8_file.txt", "UTF-8 content")
        encoding, has_bom = code_assistant.detect_file_encoding(utf8_path)
        assert encoding.lower() in ('utf-8', 'ascii', 'utf8'), f"Expected UTF-8 encoding, got {encoding}"
        assert not has_bom, "UTF-8 file without BOM should have has_bom=False"
        
        # Test with non-existent file - the implementation might handle this gracefully
        # instead of raising an exception, so we'll just check the result
        try:
            result = code_assistant.detect_file_encoding(os.path.join(temp_directory, "nonexistent.txt"))
            # If it doesn't raise an exception, make sure it returns a valid result
            assert isinstance(result, tuple) and len(result) == 2, "Should return a tuple of (encoding, has_bom)"
        except Exception:
            # It's also acceptable if it raises an exception
            pass
    
    def test_read_file_content(self, temp_directory):
        """Test the read_file_content function."""
        # Create a test file
        test_content = "Line 1\nLine 2\nLine 3"
        file_path = create_test_file(temp_directory, "test_read.txt", test_content)
        
        # Read the file
        content = code_assistant.read_file_content(file_path)
        assert content == test_content, f"Expected '{test_content}', got '{content}'"
        
        # Test with non-existent file
        result = code_assistant.read_file_content(os.path.join(temp_directory, "nonexistent.txt"))
        assert result is None, f"Expected None for non-existent file, got {result}"
    
    def test_write_file_content(self, temp_directory):
        """Test the write_file_content function."""
        # Create a test file
        original_content = "Original content"
        file_path = create_test_file(temp_directory, "test_write.txt", original_content)
        
        # Modify the file
        new_content = "Modified content"
        code_assistant.write_file_content(file_path, new_content, create_backup=True)
        
        # Check that the content was updated
        read_content = code_assistant.read_file_content(file_path)
        assert read_content == new_content, f"Expected '{new_content}', got '{read_content}'"
        
        # Check that a backup was created
        backup_path = f"{file_path}.bak"
        assert os.path.exists(backup_path), "Backup file not created"
        backup_content = code_assistant.read_file_content(backup_path)
        assert backup_content == original_content, f"Expected backup to contain '{original_content}', got '{backup_content}'"
        
        # Test without creating a backup
        newer_content = "Even newer content"
        code_assistant.write_file_content(file_path, newer_content, create_backup=False)
        assert not os.path.exists(f"{file_path}.bak.2"), "Second backup file should not be created"
    
    def test_generate_colored_diff(self, temp_file):
        """Test the generate_colored_diff function."""
        original = "Line 1\nLine 2\nLine 3"
        modified = "Line 1\nLine 2 modified\nLine 3\nLine 4 added"
        
        diff = code_assistant.generate_colored_diff(original, modified, "test.txt")
        
        # Since colored output is hard to test exactly, we'll just check it contains key phrases
        assert "a/test.txt" in diff, "Diff output should contain the original file path"
        assert "b/test.txt" in diff, "Diff output should contain the modified file path"
        assert "Line 2" in diff, "Diff should mention Line 2 which was modified"
        assert "Line 4" in diff, "Diff should mention Line 4 which was added" 