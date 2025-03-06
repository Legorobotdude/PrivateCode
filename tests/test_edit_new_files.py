"""
Tests for the enhanced edit functionality that can handle new files.
"""
import os
import pytest
from pathlib import Path
import code_assistant
from unittest.mock import patch, MagicMock

class TestEditNewFiles:
    """Tests for the enhanced edit functionality that can handle new files."""
    
    def test_handle_edit_query_new_file(self, temp_directory):
        """Test editing a new file that doesn't exist yet."""
        # Set up test file path
        test_file = os.path.join(temp_directory, "new_file.py")
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("Add a hello world function", [(test_file, None, None)], [])
            
            # Mock the read_file_content function to return None for the new file
            with patch('code_assistant.read_file_content', return_value=None):
                # Mock the get_ollama_response function to return a response with code
                mock_response = """I'll add a simple hello world function to the new file.

```python
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
```

This function simply prints "Hello, World!" when called, and the script will execute this function when run directly."""
                
                with patch('code_assistant.get_ollama_response', return_value=mock_response):
                    # Mock the extract_modified_content function to return the modified content
                    modified_content = """def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
"""
                    with patch('code_assistant.extract_modified_content', return_value=modified_content):
                        # Mock input function to simulate user confirming file creation and changes
                        with patch('builtins.input', return_value='y'):
                            # Create a conversation history
                            conversation_history = []
                            
                            # Call the function with an edit query
                            code_assistant.handle_edit_query("edit: [new_file.py] Add a hello world function", conversation_history)
                            
                            # Check that the file was created
                            assert os.path.exists(test_file), f"File {test_file} was not created"
                            
                            # Check that the file contains the expected content
                            with open(test_file, 'r') as f:
                                content = f.read()
                                assert content == modified_content, f"File content doesn't match expected content"
                            
                            # Check that the conversation history was updated
                            assert len(conversation_history) >= 2
                            assert any(msg["role"] == "system" and f"Created file '{test_file}'" in msg["content"] for msg in conversation_history)
    
    def test_handle_edit_query_new_file_cancel_creation(self, temp_directory):
        """Test canceling the creation of a new file during edit."""
        # Set up test file path
        test_file = os.path.join(temp_directory, "canceled_file.py")
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("Add a function", [(test_file, None, None)], [])
            
            # Mock the read_file_content function to return None for the new file
            with patch('code_assistant.read_file_content', return_value=None):
                # Mock input function to simulate user canceling file creation
                with patch('builtins.input', return_value='n'):
                    # Create a conversation history
                    conversation_history = []
                    
                    # Call the function with an edit query
                    code_assistant.handle_edit_query("edit: [canceled_file.py] Add a function", conversation_history)
                    
                    # Check that the file was not created
                    assert not os.path.exists(test_file), f"File {test_file} was created despite cancellation"
                    
                    # Check that the conversation history was not updated
                    assert len(conversation_history) == 0
    
    def test_handle_edit_query_new_file_in_new_directory(self, temp_directory):
        """Test editing a new file in a new directory that doesn't exist yet."""
        # Set up test file path in a new directory
        test_dir = os.path.join(temp_directory, "new_dir")
        test_file = os.path.join(test_dir, "new_file.py")
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("Add a hello world function", [(test_file, None, None)], [])
            
            # Mock the read_file_content function to return None for the new file
            with patch('code_assistant.read_file_content', return_value=None):
                # Mock the get_ollama_response function to return a response with code
                mock_response = """I'll add a simple hello world function to the new file.

```python
def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
```

This function simply prints "Hello, World!" when called, and the script will execute this function when run directly."""
                
                with patch('code_assistant.get_ollama_response', return_value=mock_response):
                    # Mock the extract_modified_content function to return the modified content
                    modified_content = """def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
"""
                    with patch('code_assistant.extract_modified_content', return_value=modified_content):
                        # Mock input function to simulate user confirming file creation and changes
                        with patch('builtins.input', return_value='y'):
                            # Create a conversation history
                            conversation_history = []
                            
                            # Call the function with an edit query
                            code_assistant.handle_edit_query(f"edit: [{test_file}] Add a hello world function", conversation_history)
                            
                            # Check that the directory was created
                            assert os.path.exists(test_dir), f"Directory {test_dir} was not created"
                            
                            # Check that the file was created
                            assert os.path.exists(test_file), f"File {test_file} was not created"
                            
                            # Check that the file contains the expected content
                            with open(test_file, 'r') as f:
                                content = f.read()
                                assert content == modified_content, f"File content doesn't match expected content"
                            
                            # Check that the conversation history was updated
                            assert len(conversation_history) >= 2
                            assert any(msg["role"] == "system" and f"Created file '{test_file}'" in msg["content"] for msg in conversation_history)
    
    def test_handle_edit_query_existing_file(self, temp_directory):
        """Test editing an existing file."""
        # Set up test file path
        test_file = os.path.join(temp_directory, "existing_file.py")
        
        # Create the file with initial content
        initial_content = """# Initial content
def initial_function():
    pass
"""
        with open(test_file, 'w') as f:
            f.write(initial_content)
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("Modify the function", [(test_file, None, None)], [])
            
            # Mock the read_file_content function to return the initial content
            with patch('code_assistant.read_file_content', return_value=initial_content):
                # Mock the get_ollama_response function to return a response with modified code
                mock_response = """I'll modify the function to print a message.

```python
# Modified content
def initial_function():
    print("Function was called")
```

Now the function will print a message when called."""
                
                with patch('code_assistant.get_ollama_response', return_value=mock_response):
                    # Mock the extract_modified_content function to return the modified content
                    modified_content = """# Modified content
def initial_function():
    print("Function was called")
"""
                    with patch('code_assistant.extract_modified_content', return_value=modified_content):
                        # Mock input function to simulate user confirming changes
                        with patch('builtins.input', return_value='y'):
                            # Create a conversation history
                            conversation_history = []
                            
                            # Call the function with an edit query
                            code_assistant.handle_edit_query("edit: [existing_file.py] Modify the function", conversation_history)
                            
                            # Check that the file contains the expected content
                            with open(test_file, 'r') as f:
                                content = f.read()
                                assert content == modified_content, f"File content doesn't match expected content"
                            
                            # Check that the conversation history was updated
                            assert len(conversation_history) >= 2 