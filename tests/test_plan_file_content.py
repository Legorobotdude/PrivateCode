"""
Tests for the file content inclusion in the planning functionality.
"""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import code_assistant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import code_assistant

@pytest.fixture
def temp_directory(tmp_path):
    """Create a temporary directory for testing."""
    return str(tmp_path)

@pytest.fixture
def temp_file_with_content(temp_directory):
    """Create a temporary file with content for testing."""
    file_path = os.path.join(temp_directory, "test_file.py")
    content = "def hello():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello()"
    
    with open(file_path, "w") as f:
        f.write(content)
    
    return file_path

@patch('code_assistant.get_ollama_response')
@patch('code_assistant.read_file_content')
def test_file_content_inclusion_in_planning_prompt(mock_read_file, mock_get_response, temp_file_with_content):
    """Test that file contents are correctly included in the planning prompt."""
    # Setup mock for read_file_content to return test content
    mock_read_file.return_value = "def hello():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello()"
    
    # Setup a test response from the LLM
    mock_get_response.return_value = """[
        {"type": "edit_file", "file_path": "test_file.py", "original_pattern": "def hello():", "new_content": "def hello_world():"}
    ]"""
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Get the file name without the path
        file_name = os.path.basename(temp_file_with_content)
        
        # Create a plan query that references the file
        plan_query = f"plan: Update the hello function in [{file_name}]"
        
        # Execute the plan query
        conversation_history = []
        code_assistant.handle_plan_query(plan_query, conversation_history)
        
        # Verify that the file content was included in the planning prompt
        planning_prompt = conversation_history[0]["content"]
        assert "Files for context:" in planning_prompt
        assert file_name in planning_prompt
        assert "def hello():" in planning_prompt
        assert "print('Hello, World!')" in planning_prompt

@patch('code_assistant.get_ollama_response')
@patch('code_assistant.read_file_content')
def test_multiple_file_paths_in_query(mock_read_file, mock_get_response, temp_directory):
    """Test that multiple file paths in the query are correctly processed."""
    # Setup mock for read_file_content to return different content based on file path
    def mock_read_file_side_effect(file_path, *args, **kwargs):
        if file_path.endswith("file1.py"):
            return "# File 1 content\nprint('File 1')"
        elif file_path.endswith("file2.py"):
            return "# File 2 content\nprint('File 2')"
        return None
    
    mock_read_file.side_effect = mock_read_file_side_effect
    
    # Create two test files
    file1_path = os.path.join(temp_directory, "file1.py")
    file2_path = os.path.join(temp_directory, "file2.py")
    
    with open(file1_path, "w") as f:
        f.write("# File 1 content\nprint('File 1')")
    
    with open(file2_path, "w") as f:
        f.write("# File 2 content\nprint('File 2')")
    
    # Setup a test response from the LLM
    mock_get_response.return_value = """[
        {"type": "edit_file", "file_path": "file1.py", "original_pattern": "print('File 1')", "new_content": "print('Updated File 1')"}
    ]"""
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Create a plan query that references both files
        plan_query = "plan: Update the print statements in [file1.py] and [file2.py]"
        
        # Execute the plan query
        conversation_history = []
        code_assistant.handle_plan_query(plan_query, conversation_history)
        
        # Verify that both file contents were included in the planning prompt
        planning_prompt = conversation_history[0]["content"]
        assert "Files for context:" in planning_prompt
        assert "file1.py" in planning_prompt and "file2.py" in planning_prompt
        assert "# File 1 content" in planning_prompt
        assert "# File 2 content" in planning_prompt

@patch('code_assistant.get_ollama_response')
@patch('code_assistant.read_file_content')
def test_edit_file_in_planning_prompt(mock_read_file, mock_get_response, temp_file_with_content):
    """Test that the edit_file step type works correctly in the planning functionality."""
    # Setup mock for read_file_content to return test content
    mock_read_file.return_value = "def hello():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    hello()"
    
    # Setup a test response from the LLM
    mock_get_response.return_value = """[
        {"type": "edit_file", "file_path": "test_file.py", "original_pattern": "def hello():", "new_content": "def hello_world():"}
    ]"""
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Get the file name without the path
        file_name = os.path.basename(temp_file_with_content)
        
        # Create a plan query that references the file
        plan_query = f"plan: Update the hello function in [{file_name}]"
        
        # Execute the plan query
        conversation_history = []
        code_assistant.handle_plan_query(plan_query, conversation_history)
        
        # Verify that the file content was included in the planning prompt
        planning_prompt = conversation_history[0]["content"]
        assert "Files for context:" in planning_prompt
        assert file_name in planning_prompt
        assert "def hello():" in planning_prompt
        
        # Verify that the plan includes the edit_file step
        generated_plan = conversation_history[1]["content"]
        assert "edit_file" in generated_plan
        assert "original_pattern" in generated_plan
        assert "new_content" in generated_plan

@patch('code_assistant.get_ollama_response')
def test_edit_file_execution(mock_get_response, temp_file_with_content):
    """Test that the edit_file step type correctly executes and modifies a file."""
    # Read the original file content
    with open(temp_file_with_content, 'r') as f:
        original_content = f.read()
    
    # Setup a test response from the LLM
    mock_get_response.return_value = """[
        {"type": "edit_file", "file_path": "%s", "original_pattern": "def hello():", "new_content": "def hello_world():"}
    ]""" % os.path.basename(temp_file_with_content)
    
    # Mock the input function to simulate user confirming the edit
    # We need to provide enough input values:
    # 1. Save the plan? (n)
    # 2. Execute the plan? (y)
    # 3. Execute this step? (y)
    # 4. Continue with next steps? (n)
    with patch('builtins.print'), patch('builtins.input', side_effect=['n', 'y', 'y', 'n']):
        # Create a plan query that references the file
        plan_query = f"plan: Update the hello function in [{os.path.basename(temp_file_with_content)}]"
        
        # Change to the directory containing the temp file to ensure relative paths work
        original_dir = os.getcwd()
        try:
            os.chdir(os.path.dirname(temp_file_with_content))
            
            # Execute the plan query
            conversation_history = []
            with patch('code_assistant.generate_colored_diff', return_value="Diff preview"):
                code_assistant.handle_plan_query(plan_query, conversation_history)
            
            # Read the updated file content
            with open(os.path.basename(temp_file_with_content), 'r') as f:
                updated_content = f.read()
            
            # Verify that the file was edited correctly
            assert "def hello_world():" in updated_content
            assert "def hello():" not in updated_content
        finally:
            os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
def test_nonexistent_file_handling(mock_get_response):
    """Test that nonexistent files are gracefully handled."""
    # Setup a test response from the LLM
    mock_get_response.return_value = """[
        {"type": "create_file", "file_path": "nonexistent.py"}
    ]"""
    
    with patch('builtins.print') as mock_print, patch('builtins.input', return_value='n'):
        # Create a plan query that references a nonexistent file
        plan_query = "plan: Update [nonexistent.py]"
        
        # Execute the plan query
        conversation_history = []
        code_assistant.handle_plan_query(plan_query, conversation_history)
        
        # Verify that a warning was printed
        warning_calls = [call for call in mock_print.call_args_list if "Warning: Could not read file nonexistent.py" in str(call)]
        assert len(warning_calls) > 0, "No warning was printed for nonexistent file"
        
        # Verify that the plan was still generated despite the missing file
        assert len(conversation_history) == 2  # Prompt and response 