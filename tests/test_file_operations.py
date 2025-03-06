"""
Tests for file operation functions in the code assistant.
"""
import os
import pytest
from tests.utils import create_test_file
import code_assistant
from unittest.mock import patch

class TestFileOperations:
    """Tests for file operations like reading, writing, and detecting encoding."""
    
    def test_detect_file_encoding(self, tmp_path):
        """Test the detect_file_encoding function with various encodings."""
        # Create test files with different encodings
        
        # UTF-8 file
        utf8_file = tmp_path / "utf8.txt"
        utf8_file.write_text("Hello, world!", encoding="utf-8")
        
        # UTF-8 with BOM
        utf8_bom_file = tmp_path / "utf8_bom.txt"
        with open(utf8_bom_file, 'wb') as f:
            f.write(b'\xef\xbb\xbf')  # UTF-8 BOM
            f.write("Hello, world!".encode('utf-8'))
        
        # UTF-16 LE file
        utf16_le_file = tmp_path / "utf16_le.txt"
        utf16_le_file.write_text("Hello, world!", encoding="utf-16-le")
        
        # UTF-16 BE file
        utf16_be_file = tmp_path / "utf16_be.txt"
        utf16_be_file.write_text("Hello, world!", encoding="utf-16-be")
        
        # Test detection
        encoding, bom = code_assistant.detect_file_encoding(str(utf8_file))
        assert encoding.lower() in ('utf-8', 'ascii'), f"Expected utf-8 or ascii, got {encoding}"
        assert not bom, "UTF-8 without BOM should have bom=False"
        
        encoding, bom = code_assistant.detect_file_encoding(str(utf8_bom_file))
        assert encoding.lower() == 'utf-8-sig', f"Expected utf-8-sig, got {encoding}"
        assert bom, "UTF-8 with BOM should have bom=True"
        
        encoding, bom = code_assistant.detect_file_encoding(str(utf16_le_file))
        assert encoding.lower() == 'utf-16-le', f"Expected utf-16-le, got {encoding}"
        assert not bom, "UTF-16-LE without BOM should have bom=False"
        
        encoding, bom = code_assistant.detect_file_encoding(str(utf16_be_file))
        assert encoding.lower() == 'utf-16-be', f"Expected utf-16-be, got {encoding}"
        assert not bom, "UTF-16-BE without BOM should have bom=False"
    
    @patch('chardet.detect')
    def test_detect_file_encoding_with_chardet(self, mock_detect, tmp_path):
        """Test the detect_file_encoding function with mocked chardet."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!", encoding="utf-8")
        
        # Mock chardet.detect to return a specific result
        mock_detect.return_value = {
            'encoding': 'utf-8',
            'confidence': 0.99
        }
        
        # Test detection
        encoding, bom = code_assistant.detect_file_encoding(str(test_file))
        assert encoding == 'utf-8', f"Expected utf-8, got {encoding}"
        assert not bom, "Should have bom=False"
        
        # Verify chardet was called
        mock_detect.assert_called()
        
        # Test with low confidence
        mock_detect.reset_mock()
        mock_detect.return_value = {
            'encoding': 'iso-8859-1',
            'confidence': 0.6
        }
        
        encoding, bom = code_assistant.detect_file_encoding(str(test_file))
        assert encoding == 'iso-8859-1', f"Expected iso-8859-1, got {encoding}"
        assert not bom, "Should have bom=False"
        
    @patch('chardet.detect')
    def test_detect_file_encoding_with_chardet_none(self, mock_detect, tmp_path):
        """Test the detect_file_encoding function when chardet returns None."""
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, world!", encoding="utf-8")
        
        # Mock chardet.detect to return None for encoding
        mock_detect.return_value = {
            'encoding': None,
            'confidence': 0.0
        }
        
        # Test detection
        encoding, bom = code_assistant.detect_file_encoding(str(test_file))
        assert encoding == 'utf-8', f"Expected utf-8 fallback, got {encoding}"
        assert not bom, "Should have bom=False"
    
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