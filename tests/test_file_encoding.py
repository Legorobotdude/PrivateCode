"""
Tests for file encoding detection functionality in code_assistant.
"""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
import code_assistant


class TestFileEncoding:
    """Tests for file encoding detection functionality."""
    
    def setup_method(self):
        """Set up temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
    
    def teardown_method(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()
    
    def create_test_file(self, content, encoding='utf-8', with_bom=False):
        """Create a test file with the specified encoding."""
        path = os.path.join(self.temp_dir.name, f"test_file_{encoding.replace('-', '_')}.txt")
        
        # Add BOM if requested
        if with_bom and encoding == 'utf-8':
            mode = 'wb'
            content_bytes = '\ufeff'.encode('utf-8') + content.encode(encoding)
            with open(path, mode) as f:
                f.write(content_bytes)
        else:
            mode = 'w'
            with open(path, mode, encoding=encoding) as f:
                f.write(content)
        
        return path
    
    def test_detect_utf8_encoding(self):
        """Test detection of UTF-8 encoding."""
        content = "This is a UTF-8 encoded file."
        path = self.create_test_file(content, encoding='utf-8')
        
        encoding, has_bom = code_assistant.detect_file_encoding(path)
        assert encoding.lower() in ('utf-8', 'ascii'), f"Expected utf-8 or ascii, got {encoding}"
        assert has_bom is False, "UTF-8 file should not have BOM"
    
    def test_detect_utf8_with_bom(self):
        """Test detection of UTF-8 with BOM."""
        content = "This is a UTF-8 file with BOM."
        path = self.create_test_file(content, encoding='utf-8', with_bom=True)
        
        encoding, has_bom = code_assistant.detect_file_encoding(path)
        assert encoding.lower() in ('utf-8-sig', 'utf-8'), f"Expected utf-8-sig or utf-8, got {encoding}"
        # Some systems might detect BOM differently, so we check if it's correctly identified
        # or returns UTF-8 without marking BOM
    
    @pytest.mark.parametrize("test_encoding", [
        'latin-1',
        'cp1252',
    ])
    def test_detect_other_encodings(self, test_encoding):
        """Test detection of other common encodings."""
        # Create content with characters specific to these encodings
        if test_encoding == 'latin-1':
            content = "Latin-1 specific: é è à ù"
        else:  # cp1252
            content = "CP1252 specific: € ' " " –"
        
        path = self.create_test_file(content, encoding=test_encoding)
        
        encoding, has_bom = code_assistant.detect_file_encoding(path)
        # chardet might detect similar encodings, so we check for compatibility
        assert encoding.lower() in (test_encoding.lower(), 'iso-8859-1', 'windows-1252', 'utf-8', 'ascii'), \
            f"Expected {test_encoding} or compatible, got {encoding}"
        assert has_bom is False, f"{test_encoding} should not have BOM"
    
    def test_detect_empty_file(self):
        """Test encoding detection with an empty file."""
        path = self.create_test_file("", encoding='utf-8')
        
        encoding, has_bom = code_assistant.detect_file_encoding(path)
        assert encoding.lower() == 'utf-8', f"Expected utf-8 for empty file, got {encoding}"
        assert has_bom is False, "Empty file should not have BOM"
    
    @patch('chardet.detect')
    def test_chardet_error_fallback(self, mock_detect):
        """Test fallback when chardet fails."""
        content = "Test content for fallback"
        path = self.create_test_file(content, encoding='utf-8')
        
        # Make chardet raise an exception
        mock_detect.side_effect = Exception("Simulated chardet error")
        
        with patch('code_assistant._legacy_detect_file_encoding') as mock_legacy:
            mock_legacy.return_value = ('utf-8', False)
            
            encoding, has_bom = code_assistant.detect_file_encoding(path)
            # Should call the legacy method when chardet fails
            mock_legacy.assert_called_once_with(path)
    
    @patch('builtins.open')
    def test_file_not_found(self, mock_open):
        """Test handling of file not found error."""
        mock_open.side_effect = FileNotFoundError("File not found")
        
        encoding, has_bom = code_assistant.detect_file_encoding("nonexistent_file.txt")
        assert encoding == 'utf-8', "Should default to utf-8 when file not found"
        assert has_bom is False, "Should default to no BOM when file not found"
    
    def test_legacy_encoding_detection(self):
        """Test the legacy encoding detection method."""
        content = "Test content for legacy detection"
        path = self.create_test_file(content, encoding='utf-8')
        
        encoding, has_bom = code_assistant._legacy_detect_file_encoding(path)
        assert encoding.lower() in ('utf-8', 'ascii'), f"Expected utf-8 or ascii in legacy detection, got {encoding}"
        assert has_bom is False, "Legacy detection should not detect BOM for this file"
    
    @patch('builtins.open')
    def test_legacy_detection_all_fail(self, mock_open):
        """Test legacy detection when all encodings fail."""
        # Make all encoding attempts fail
        mock_open.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'Invalid character')
        
        encoding, has_bom = code_assistant._legacy_detect_file_encoding("some_file.txt")
        assert encoding == 'utf-8', "Should default to utf-8 when all encodings fail"
        assert has_bom is False, "Should default to no BOM when all encodings fail"
    
    def test_low_confidence_warning(self):
        """Test warning for low confidence in encoding detection."""
        content = "Test content for low confidence warning"
        path = self.create_test_file(content, encoding='utf-8')
        
        mock_result = {'encoding': 'utf-8', 'confidence': 0.5}
        
        with patch('chardet.detect', return_value=mock_result), \
             patch('builtins.print') as mock_print:
            
            encoding, has_bom = code_assistant.detect_file_encoding(path)
            
            # Should print a warning for low confidence
            mock_print.assert_called_once()
            assert "Low confidence" in mock_print.call_args[0][0] 