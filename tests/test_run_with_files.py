"""
Tests for the enhanced run functionality that includes file context.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
import code_assistant

class TestRunWithFiles:
    """Tests for the enhanced run functionality that includes file context."""
    
    def test_handle_run_query_with_file_context(self, temp_directory):
        """Test running a command with file context."""
        # Create a test file
        test_file = os.path.join(temp_directory, "test_script.py")
        with open(test_file, 'w') as f:
            f.write("print('Hello, World!')")
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("Run this script", [(test_file, None, None)], [])
            
            # Mock the get_ollama_response function to return a response with a command
            mock_response = """Based on the file content, I suggest running the Python script:

```bash
python test_script.py
```

This will execute the script and print "Hello, World!" to the console."""
            
            with patch('code_assistant.get_ollama_response', return_value=mock_response):
                # Mock the extract_suggested_command function to return the command
                with patch('code_assistant.extract_suggested_command', return_value="python test_script.py"):
                    # Mock the is_safe_command function to return True
                    with patch('code_assistant.is_safe_command', return_value=(True, None)):
                        # Mock the execute_command function to return a mock output
                        with patch('code_assistant.execute_command', return_value="Hello, World!"):
                            # Mock input function to simulate user confirming execution
                            with patch('builtins.input', return_value='y'):
                                # Create a conversation history
                                conversation_history = []
                                
                                # Call the function with a run query
                                code_assistant.handle_run_query(f"run: [test_script.py] Run this script", conversation_history)
                                
                                # Check that the conversation history was updated
                                assert len(conversation_history) == 3
                                assert conversation_history[0]["role"] == "user"
                                assert "Command Request: Run this script" in conversation_history[0]["content"]
                                assert f"File: {test_file}" in conversation_history[0]["content"]
                                assert "print('Hello, World!')" in conversation_history[0]["content"]
                                assert conversation_history[1]["role"] == "assistant"
                                assert conversation_history[2]["role"] == "system"
                                assert "python test_script.py" in conversation_history[2]["content"]
                                assert "Hello, World!" in conversation_history[2]["content"]
    
    def test_handle_run_query_with_multiple_files(self, temp_directory):
        """Test running a command with multiple file contexts."""
        # Create test files
        test_file1 = os.path.join(temp_directory, "file1.py")
        with open(test_file1, 'w') as f:
            f.write("def hello():\n    print('Hello')")
        
        test_file2 = os.path.join(temp_directory, "file2.py")
        with open(test_file2, 'w') as f:
            f.write("from file1 import hello\n\nhello()\nprint('World!')")
        
        # Mock the extract_file_paths_and_urls function to return our test files
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test files
            mock_extract.return_value = ("Run these files", [(test_file1, None, None), (test_file2, None, None)], [])
            
            # Mock the get_ollama_response function to return a response with a command
            mock_response = """Based on the file content, I suggest running file2.py which imports and uses file1.py:

```bash
python file2.py
```

This will execute file2.py which imports the hello function from file1.py and prints "Hello" followed by "World!"."""
            
            with patch('code_assistant.get_ollama_response', return_value=mock_response):
                # Mock the extract_suggested_command function to return the command
                with patch('code_assistant.extract_suggested_command', return_value="python file2.py"):
                    # Mock the is_safe_command function to return True
                    with patch('code_assistant.is_safe_command', return_value=(True, None)):
                        # Mock the execute_command function to return a mock output
                        with patch('code_assistant.execute_command', return_value="Hello\nWorld!"):
                            # Mock input function to simulate user confirming execution
                            with patch('builtins.input', return_value='y'):
                                # Create a conversation history
                                conversation_history = []
                                
                                # Call the function with a run query
                                code_assistant.handle_run_query(f"run: [file1.py] [file2.py] Run these files", conversation_history)
                                
                                # Check that the conversation history was updated
                                assert len(conversation_history) == 3
                                assert conversation_history[0]["role"] == "user"
                                assert "Command Request: Run these files" in conversation_history[0]["content"]
                                assert f"File: {test_file1}" in conversation_history[0]["content"]
                                assert f"File: {test_file2}" in conversation_history[0]["content"]
                                assert "def hello():" in conversation_history[0]["content"]
                                assert "from file1 import hello" in conversation_history[0]["content"]
                                assert conversation_history[1]["role"] == "assistant"
                                assert conversation_history[2]["role"] == "system"
                                assert "python file2.py" in conversation_history[2]["content"]
                                assert "Hello\nWorld!" in conversation_history[2]["content"]
    
    def test_handle_run_query_with_unsafe_command(self, temp_directory):
        """Test handling an unsafe command."""
        # Create a test file
        test_file = os.path.join(temp_directory, "test_script.py")
        with open(test_file, 'w') as f:
            f.write("print('Hello, World!')")
        
        # Mock the extract_file_paths_and_urls function to return our test file
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file
            mock_extract.return_value = ("Run this script", [(test_file, None, None)], [])
            
            # Mock the get_ollama_response function to return a response with an unsafe command
            mock_response = """Based on the file content, I suggest running the Python script:

```bash
rm -rf /
```

This will execute the script."""
            
            with patch('code_assistant.get_ollama_response', return_value=mock_response):
                # Mock the extract_suggested_command function to return the command
                with patch('code_assistant.extract_suggested_command', return_value="rm -rf /"):
                    # Mock the is_safe_command function to return False
                    with patch('code_assistant.is_safe_command', return_value=(False, "Command contains potentially dangerous operation: 'rm'")):
                        # Mock input function to simulate user canceling execution
                        with patch('builtins.input', return_value='n'):
                            # Create a conversation history
                            conversation_history = []
                            
                            # Call the function with a run query
                            code_assistant.handle_run_query(f"run: [test_script.py] Run this script", conversation_history)
                            
                            # Check that the conversation history was updated with only the user and assistant messages
                            assert len(conversation_history) == 2
                            assert conversation_history[0]["role"] == "user"
                            assert conversation_history[1]["role"] == "assistant"
    
    def test_handle_run_query_with_line_range(self, temp_directory):
        """Test running a command with file context including line ranges."""
        # Create a test file with multiple lines
        test_file = os.path.join(temp_directory, "multi_line.py")
        with open(test_file, 'w') as f:
            f.write("# Line 1\n# Line 2\n# Line 3\nprint('Line 4')\n# Line 5\n# Line 6")
        
        # Mock the extract_file_paths_and_urls function to return our test file with line range
        with patch('code_assistant.extract_file_paths_and_urls') as mock_extract:
            # Set up the mock to return our test file with line range (lines 3-5)
            mock_extract.return_value = ("Run this script", [(test_file, 3, 5)], [])
            
            # Mock the read_file_content function to return only the specified lines
            with patch('code_assistant.read_file_content', return_value="# Line 3\nprint('Line 4')\n# Line 5"):
                # Mock the get_ollama_response function to return a response with a command
                mock_response = """Based on the file content, I suggest running the Python script:

```bash
python multi_line.py
```

This will execute the script and print "Line 4" to the console."""
                
                with patch('code_assistant.get_ollama_response', return_value=mock_response):
                    # Mock the extract_suggested_command function to return the command
                    with patch('code_assistant.extract_suggested_command', return_value="python multi_line.py"):
                        # Mock the is_safe_command function to return True
                        with patch('code_assistant.is_safe_command', return_value=(True, None)):
                            # Mock the execute_command function to return a mock output
                            with patch('code_assistant.execute_command', return_value="Line 4"):
                                # Mock input function to simulate user confirming execution
                                with patch('builtins.input', return_value='y'):
                                    # Create a conversation history
                                    conversation_history = []
                                    
                                    # Call the function with a run query including line range
                                    code_assistant.handle_run_query(f"run: [multi_line.py:3-5] Run this script", conversation_history)
                                    
                                    # Check that the conversation history was updated
                                    assert len(conversation_history) == 3
                                    assert conversation_history[0]["role"] == "user"
                                    assert "Command Request: Run this script" in conversation_history[0]["content"]
                                    assert f"File: {test_file} (lines 3-5)" in conversation_history[0]["content"]
                                    assert "# Line 3" in conversation_history[0]["content"]
                                    assert "print('Line 4')" in conversation_history[0]["content"]
                                    assert "# Line 5" in conversation_history[0]["content"]
                                    assert conversation_history[1]["role"] == "assistant"
                                    assert conversation_history[2]["role"] == "system"
                                    assert "python multi_line.py" in conversation_history[2]["content"]
                                    assert "Line 4" in conversation_history[2]["content"] 