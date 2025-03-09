"""
Extended tests for content extraction functionality in code_assistant.
"""
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
import code_assistant


class TestContentExtractionExtended:
    """Extended tests for content extraction functionality."""
    
    def setup_method(self):
        """Set up temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.orig_working_dir = code_assistant.WORKING_DIRECTORY
    
    def teardown_method(self):
        """Clean up temporary directory."""
        code_assistant.WORKING_DIRECTORY = self.orig_working_dir
        self.temp_dir.cleanup()
        
    def create_test_file(self, filename, content):
        """Create a test file with the specified content."""
        file_path = os.path.join(self.temp_dir.name, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return file_path
    
    def test_extract_file_paths_standard_cases(self):
        """Test extracting file paths for standard cases."""
        # Test with a simple file path
        query = "Show me [myfile.py]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me"
        assert len(file_items) == 1
        assert file_items[0][0] == "myfile.py"
        assert file_items[0][1] is None
        assert file_items[0][2] is None
        
        # Test with line range
        query = "Show me [file.py:10-20]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me"
        assert len(file_items) == 1
        assert file_items[0][0] == "file.py"
        assert file_items[0][1] == 10
        assert file_items[0][2] == 20
    
    def test_extract_file_paths_with_complex_line_ranges(self):
        """Test extracting file paths with complex line range specifications."""
        # Test with a single line number (implementation treats as a range from n to n+1)
        query = "Check line 42 in [important.py:42]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Check line 42 in"
        assert len(file_items) == 1
        assert file_items[0][0] == "important.py"
        assert file_items[0][1] == 42
        # The implementation might treat single line as range from n to n+1
        
        # Test with large line numbers
        query = "Show me lines [big_file.txt:10000-10050]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Show me lines"
        assert len(file_items) == 1
        assert file_items[0][0] == "big_file.txt"
        assert file_items[0][1] == 10000
        assert file_items[0][2] == 10050
    
    def test_extract_multiple_interleaved_items(self):
        """Test extracting multiple interleaved file paths and URLs."""
        query = "Compare [file1.py] with [https://example.com] and also [file2.py:10-20]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Compare  with  and also"
        assert len(file_items) == 2
        assert file_items[0][0] == "file1.py"
        assert file_items[1][0] == "file2.py"
        assert file_items[1][1] == 10
        assert file_items[1][2] == 20
        assert len(urls) == 1
        assert urls[0] == "https://example.com"
        
        # Test with multiple URLs and files
        query = "Check [https://site1.com], [file.py], and [https://site2.com]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Check , , and"
        assert len(file_items) == 1
        assert len(urls) == 2
        assert "https://site1.com" in urls
        assert "https://site2.com" in urls
    
    def test_url_extraction_variants(self):
        """Test extracting various URL formats."""
        # Test with standard HTTP URLs
        query = "Visit [http://example.com]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Visit"
        assert len(urls) == 1
        assert urls[0] == "http://example.com"
        
        # Test with HTTPS URLs
        query = "Check [https://example.com/path/to/resource]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Check"
        assert len(urls) == 1
        assert urls[0] == "https://example.com/path/to/resource"
        
        # Test with URLs containing query parameters
        query = "Look at [https://example.com/search?q=python&lang=en]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "Look at"
        assert len(urls) == 1
        assert urls[0] == "https://example.com/search?q=python&lang=en"
        
        # Test with URLs containing fragments
        query = "See [https://example.com/docs#section-3.2]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        assert clean_query == "See"
        assert len(urls) == 1
        assert urls[0] == "https://example.com/docs#section-3.2"
    
    def test_integration_with_file_reading(self):
        """Test integration of file path extraction with file reading."""
        # Create test files
        file1 = self.create_test_file("test1.txt", "Line 1\nLine 2\nLine 3\nLine 4\nLine 5")
        file2 = self.create_test_file("test2.txt", "First\nSecond\nThird\nFourth\nFifth")
        
        # Set working directory for relative paths
        code_assistant.WORKING_DIRECTORY = self.temp_dir.name
        
        # Test reading specific lines from a file referenced in a query
        query = f"Show me lines 2-4 in [test1.txt:2-4]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        
        # Check that extraction worked
        assert clean_query == "Show me lines 2-4 in"
        assert len(file_items) == 1
        assert file_items[0][0] == "test1.txt"
        assert file_items[0][1] == 2
        assert file_items[0][2] == 4
        
        # Read the file using the extracted information
        file_path, start_line, end_line = file_items[0]
        content = code_assistant.read_file_content(file_path, start_line, end_line)
        
        # Check that correct content was read
        assert "Line 2\nLine 3\nLine 4" in content
        assert "Line 1" not in content
        assert "Line 5" not in content
    
    def test_get_edit_file_paths_basic(self):
        """Test get_edit_file_paths with basic cases."""
        # Test with a simple file path
        file_paths = code_assistant.get_edit_file_paths("[myfile.py]")
        assert len(file_paths) == 1
        assert "myfile.py" in file_paths
        
        # Test with multiple file paths
        file_paths = code_assistant.get_edit_file_paths("[file1.py] and [file2.py]")
        assert len(file_paths) == 2
        assert "file1.py" in file_paths
        assert "file2.py" in file_paths
        
        # Test with line ranges (should be stripped)
        file_paths = code_assistant.get_edit_file_paths("[file.py:10-20]")
        assert len(file_paths) == 1
        assert "file.py" in file_paths
    
    def test_handling_invalid_inputs(self):
        """Test handling of invalid inputs for content extraction."""
        # Test with empty query
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls("")
        assert clean_query == ""
        assert len(file_items) == 0
        assert len(urls) == 0
        
        # Test with unclosed brackets
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls("Look at [file.py")
        assert "Look at [file.py" in clean_query  # Current implementation doesn't change the query
        assert len(file_items) == 0
        
        # Test with empty brackets
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls("Look at []")
        # Current implementation keeps the brackets in case of empty content
        assert "Look at []" in clean_query
        assert len(file_items) == 0
        
        # Test with invalid line range format
        query = "Check [file.py:invalid]"
        clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
        # The function should handle this gracefully without crashing
        assert "Check" in clean_query 