"""
Tests for file creation functionality in the code assistant.
"""
import os
import pytest
from pathlib import Path
import code_assistant
from unittest.mock import patch, MagicMock

class TestFileCreation:
    """Tests for the file creation functionality."""
    
    def test_is_create_query(self):
        """Test the is_create_query function."""
        # Test with create: prefix
        assert code_assistant.is_create_query("create: [file.py]") is True
        # Test with create prefix
        assert code_assistant.is_create_query("create [file.py]") is True
        # Test with uppercase
        assert code_assistant.is_create_query("CREATE: [file.py]") is True
        # Test with mixed case
        assert code_assistant.is_create_query("Create: [file.py]") is True
        # Test with non-create query
        assert code_assistant.is_create_query("edit: [file.py]") is False
        assert code_assistant.is_create_query("search: python file creation") is False
        assert code_assistant.is_create_query("How do I create a file?") is False
    
    def test_extract_create_query(self):
        """Test the extract_create_query function."""
        # Test with create: prefix
        assert code_assistant.extract_create_query("create: [file.py]") == "[file.py]"
        # Test with create prefix
        assert code_assistant.extract_create_query("create [file.py]") == "[file.py]"
        # Test with uppercase
        assert code_assistant.extract_create_query("CREATE: [file.py]") == "[file.py]"
        # Test with mixed case
        assert code_assistant.extract_create_query("Create: [file.py]") == "[file.py]"
        # Test with additional text
        assert code_assistant.extract_create_query("create: [file.py] with some content") == "[file.py] with some content"
    
    def test_handle_create_query(self, temp_directory):
        """Test the handle_create_query function."""
        # Set up test file path
        test_file = os.path.join(temp_directory, "test_create.py")
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("", [(test_file, None, None)], [])
            
            # Mock input function to simulate user confirmation
            with patch('builtins.input', return_value='y'):
                # Create a conversation history
                conversation_history = []
                
                # Call the function with a create query
                code_assistant.handle_create_query("create: [test_file]", conversation_history)
                
                # Check that the file was created
                assert os.path.exists(test_file), f"File {test_file} was not created"
                
                # Check that the conversation history was updated
                assert len(conversation_history) == 1
                assert conversation_history[0]["role"] == "system"
                assert f"Created file '{test_file}'" in conversation_history[0]["content"]
    
    def test_handle_create_query_existing_file(self, temp_directory):
        """Test the handle_create_query function with an existing file."""
        # Set up test file path
        test_file = os.path.join(temp_directory, "existing_file.py")
        
        # Create the file first
        Path(test_file).touch()
        assert os.path.exists(test_file), f"Failed to create test file {test_file}"
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("", [(test_file, None, None)], [])
            
            # Mock input function to simulate user declining to overwrite
            with patch('builtins.input', return_value='n'):
                # Create a conversation history
                conversation_history = []
                
                # Call the function with a create query
                code_assistant.handle_create_query("create: [existing_file]", conversation_history)
                
                # Check that the conversation history was not updated
                assert len(conversation_history) == 0
            
            # Mock input function to simulate user confirming overwrite
            with patch('builtins.input', side_effect=['y', 'y']):
                # Create a conversation history
                conversation_history = []
                
                # Get the original modification time
                original_mtime = os.path.getmtime(test_file)
                
                # Call the function with a create query
                code_assistant.handle_create_query("create: [existing_file]", conversation_history)
                
                # Check that the file was modified (by checking modification time)
                assert os.path.getmtime(test_file) >= original_mtime, f"File {test_file} was not modified"
                
                # Check that the conversation history was updated
                assert len(conversation_history) == 1
                assert conversation_history[0]["role"] == "system"
                assert f"Created file '{test_file}'" in conversation_history[0]["content"]
    
    def test_handle_create_query_cancel(self, temp_directory):
        """Test canceling file creation."""
        # Set up test file path
        test_file = os.path.join(temp_directory, "canceled_file.py")
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("", [(test_file, None, None)], [])
            
            # Mock input function to simulate user canceling creation
            with patch('builtins.input', return_value='n'):
                # Create a conversation history
                conversation_history = []
                
                # Call the function with a create query
                code_assistant.handle_create_query("create: [canceled_file]", conversation_history)
                
                # Check that the file was not created
                assert not os.path.exists(test_file), f"File {test_file} was created despite cancellation"
                
                # Check that the conversation history was not updated
                assert len(conversation_history) == 0
    
    def test_handle_create_query_multiple_files(self, temp_directory):
        """Test creating multiple files."""
        # Set up test file paths
        test_file1 = os.path.join(temp_directory, "file1.py")
        test_file2 = os.path.join(temp_directory, "file2.py")
        
        # Mock the extract_file_paths_and_urls function to return our test files
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test files
            mock_extract.return_value = ("", [(test_file1, None, None), (test_file2, None, None)], [])
            
            # Mock input function to simulate user confirming creation for both files
            with patch('builtins.input', return_value='y'):
                # Create a conversation history
                conversation_history = []
                
                # Call the function with a create query for multiple files
                code_assistant.handle_create_query("create: [file1] [file2]", conversation_history)
                
                # Check that both files were created
                assert os.path.exists(test_file1), f"File {test_file1} was not created"
                assert os.path.exists(test_file2), f"File {test_file2} was not created"
                
                # Check that the conversation history was updated for both files
                assert len(conversation_history) == 2
                assert conversation_history[0]["role"] == "system"
                assert conversation_history[1]["role"] == "system"
                assert f"Created file '{test_file1}'" in conversation_history[0]["content"]
                assert f"Created file '{test_file2}'" in conversation_history[1]["content"] 