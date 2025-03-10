"""
Specific tests for UTF-32 encoding detection.
"""
import os
import tempfile
import pytest
from unittest.mock import patch
import code_assistant


class TestUTF32Detection:
    """Tests specifically focused on UTF-32 encoding detection."""
    
    def setup_method(self):
        """Set up temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Clean up temporary directory."""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_utf32_le_with_bom_detection(self):
        """Test detection of UTF-32-LE with BOM."""
        file_path = os.path.join(self.temp_dir, "utf32_le_bom.txt")
        
        # Create a UTF-32-LE file with BOM
        with open(file_path, 'wb') as f:
            # UTF-32-LE BOM
            f.write(b'\xff\xfe\x00\x00')
            # UTF-32-LE encoded content
            f.write("Hello, UTF-32-LE world!".encode('utf-32-le'))
        
        # Detect encoding
        encoding, has_bom = code_assistant.detect_file_encoding(file_path)
        
        # Should correctly identify UTF-32-LE with BOM
        assert encoding.lower() == 'utf-32-le', f"Expected utf-32-le, got {encoding}"
        assert has_bom is True, "Should detect BOM for UTF-32-LE with BOM"
    
    def test_utf32_be_with_bom_detection(self):
        """Test detection of UTF-32-BE with BOM."""
        file_path = os.path.join(self.temp_dir, "utf32_be_bom.txt")
        
        # Create a UTF-32-BE file with BOM
        with open(file_path, 'wb') as f:
            # UTF-32-BE BOM
            f.write(b'\x00\x00\xfe\xff')
            # UTF-32-BE encoded content
            f.write("Hello, UTF-32-BE world!".encode('utf-32-be'))
        
        # Detect encoding
        encoding, has_bom = code_assistant.detect_file_encoding(file_path)
        
        # Should correctly identify UTF-32-BE with BOM
        assert encoding.lower() == 'utf-32-be', f"Expected utf-32-be, got {encoding}"
        assert has_bom is True, "Should detect BOM for UTF-32-BE with BOM"
    
    def test_utf32_le_without_bom_detection(self):
        """Test detection of UTF-32-LE without BOM."""
        file_path = os.path.join(self.temp_dir, "utf32_le_no_bom.txt")
        
        # Create a UTF-32-LE file without BOM
        with open(file_path, 'wb') as f:
            # UTF-32-LE encoded ASCII content (no BOM)
            f.write("ABCDEFGHIJ".encode('utf-32-le'))
        
        # Detect encoding
        encoding, has_bom = code_assistant.detect_file_encoding(file_path)
        
        # Should correctly identify UTF-32-LE without BOM
        assert encoding.lower() == 'utf-32-le', f"Expected utf-32-le, got {encoding}"
        assert has_bom is False, "Should not detect BOM for UTF-32-LE without BOM"
    
    def test_utf32_be_without_bom_detection(self):
        """Test detection of UTF-32-BE without BOM."""
        file_path = os.path.join(self.temp_dir, "utf32_be_no_bom.txt")
        
        # Create a UTF-32-BE file without BOM
        with open(file_path, 'wb') as f:
            # UTF-32-BE encoded ASCII content (no BOM)
            f.write("ABCDEFGHIJ".encode('utf-32-be'))
        
        # Detect encoding
        encoding, has_bom = code_assistant.detect_file_encoding(file_path)
        
        # Should correctly identify UTF-32-BE without BOM
        assert encoding.lower() == 'utf-32-be', f"Expected utf-32-be, got {encoding}"
        assert has_bom is False, "Should not detect BOM for UTF-32-BE without BOM"
    
    def test_utf32_full_roundtrip(self):
        """Test full round-trip reading and writing of UTF-32 content."""
        # Test content with emojis and various Unicode characters
        test_content = "UTF-32 test: Hello, World! 😀 🌍 🚀 ❤️ 你好，世界！"
        
        # Test both UTF-32-LE and UTF-32-BE
        for encoding in ['utf-32-le', 'utf-32-be']:
            file_path = os.path.join(self.temp_dir, f"utf32_{encoding}_roundtrip.txt")
            
            # Write content with specified encoding
            with open(file_path, 'wb') as f:
                # Add appropriate BOM
                if encoding == 'utf-32-le':
                    f.write(b'\xff\xfe\x00\x00')
                else:  # utf-32-be
                    f.write(b'\x00\x00\xfe\xff')
                # Write content
                f.write(test_content.encode(encoding))
            
            # Read content back using code_assistant's read_file_content
            content = code_assistant.read_file_content(file_path)
            
            # Verify content is correctly read
            assert test_content in content, f"Content read with {encoding} should match original" 