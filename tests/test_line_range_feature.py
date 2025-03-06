"""
Tests for the line range feature in the code assistant.
"""
import os
import pytest
from tests.utils import create_test_file
import code_assistant

class TestLineRangeFeature:
    """Tests for the line range feature that allows reading specific lines from files."""
    
    def test_read_file_content_with_line_range(self, temp_directory):
        """Test reading specific line ranges from a file."""
        # Create a test file with multiple lines
        test_content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8\nLine 9\nLine 10"
        file_path = create_test_file(temp_directory, "test_lines.txt", test_content)
        
        # Test reading the entire file
        content = code_assistant.read_file_content(file_path)
        assert content == test_content, "Should read the entire file when no line range is specified"
        
        # Test reading specific line range
        content = code_assistant.read_file_content(file_path, 2, 4)
        assert "Line 2\nLine 3\nLine 4" in content, "Should read lines 2-4"
        
        # Test reading from a specific line to the end
        content = code_assistant.read_file_content(file_path, 8, None)
        assert "Line 8\nLine 9\nLine 10" in content, "Should read from line 8 to the end"
        
        # Test reading from the beginning to a specific line
        content = code_assistant.read_file_content(file_path, None, 3)
        assert "Line 1\nLine 2\nLine 3" in content, "Should read from the beginning to line 3"
        
        # Test reading a single line
        content = code_assistant.read_file_content(file_path, 5, 5)
        assert "Line 5" in content, "Should read only line 5"
        
        # Test with out-of-range line numbers
        content = code_assistant.read_file_content(file_path, 100, 200)
        assert "total lines" in content, "Should handle out-of-range line numbers gracefully"
        
        # Test with negative line numbers (should be treated as 1)
        content = code_assistant.read_file_content(file_path, -5, 3)
        assert "Line 1\nLine 2\nLine 3" in content, "Should treat negative start line as 1"
    
    def test_extract_file_paths_and_urls(self):
        """Test extracting file paths with line ranges from queries."""
        # Test with a simple file path
        query = "Show me the code in [file.py]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me the code in"
        assert len(file_items) == 1
        assert file_items[0] == ("file.py", None, None)
        
        # Test with a file path and line range
        query = "Show me lines 10-20 in [file.py:10-20]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me lines 10-20 in"
        assert len(file_items) == 1
        assert file_items[0] == ("file.py", 10, 20)
        
        # Test with a file path and start line only
        query = "Show me from line 5 onwards in [file.py:5-]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me from line 5 onwards in"
        assert len(file_items) == 1
        assert file_items[0] == ("file.py", 5, None)
        
        # Test with a file path and end line only
        query = "Show me up to line 15 in [file.py:-15]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me up to line 15 in"
        assert len(file_items) == 1
        assert file_items[0] == ("file.py", None, 15)
        
        # Test with a file path and single line
        query = "Show me line 7 in [file.py:7]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me line 7 in"
        assert len(file_items) == 1
        assert file_items[0][0] == "file.py"
        assert file_items[0][1] == 7
        
        # Test with multiple file paths and line ranges
        query = "Compare [file1.py:1-10] with [file2.py:5-15]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Compare  with"
        assert len(file_items) == 2
        assert file_items[0] == ("file1.py", 1, 10)
        assert file_items[1] == ("file2.py", 5, 15)
        
        # Test with a URL
        query = "Check this [https://example.com]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Check this"
        assert len(urls) == 1
        assert urls[0] == "https://example.com"
        
        # Test with invalid line range format
        query = "Show me [file.py:invalid]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me"
        assert len(file_items) == 1
        assert file_items[0][0] == "file.py"
        # The implementation should handle invalid line ranges gracefully
    
    def test_get_edit_file_paths_compatibility(self):
        """Test that get_edit_file_paths maintains backward compatibility."""
        # Test with a simple file path
        file_paths = code_assistant.get_edit_file_paths("[file.py]")
        assert len(file_paths) == 1
        assert file_paths[0] == "file.py"
        
        # Test with multiple file paths
        file_paths = code_assistant.get_edit_file_paths("[file1.py] and [file2.py]")
        assert len(file_paths) == 2
        assert "file1.py" in file_paths
        assert "file2.py" in file_paths
        
        # Test with file paths containing line ranges
        # The function should strip the line ranges and return just the file paths
        file_paths = code_assistant.get_edit_file_paths("[file1.py:10-20] and [file2.py:5-]")
        assert len(file_paths) == 2
        assert "file1.py" in file_paths
        assert "file2.py" in file_paths 