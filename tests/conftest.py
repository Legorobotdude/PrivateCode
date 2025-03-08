"""
Configuration and fixtures for pytest.
"""
import os
import sys
import pytest
import tempfile
import shutil

# Add the parent directory to the path so we can import code_assistant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import code_assistant

@pytest.fixture
def mock_ollama_response():
    """Returns a mock response for the Ollama API."""
    return {
        "message": {
            "content": "This is a mock response from the Ollama API."
        }
    }

@pytest.fixture
def temp_directory():
    """Creates a temporary directory for testing file operations."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def temp_file():
    """Creates a temporary file for testing."""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    with open(path, 'w') as f:
        f.write("Test content for file operations\nLine 2\nLine 3\n")
    yield path
    os.unlink(path)

@pytest.fixture
def mock_timeout_responses():
    """Fixture providing a collection of mock responses for testing timeout functionality."""
    
    # Save original timeout value
    original_timeout = code_assistant.DEFAULT_TIMEOUT
    
    # Create various timeout values for testing
    test_timeout_values = {
        "valid": 120,
        "negative": -10,
        "zero": 0,
        "string": "not_a_number",
        "very_large": 9999
    }
    
    yield test_timeout_values
    
    # Restore original timeout value
    code_assistant.DEFAULT_TIMEOUT = original_timeout 

@pytest.fixture
def mock_plan_prompt():
    """Fixture providing a mock plan prompt and expected JSON response."""
    
    plan_query = "Create a simple Python script that prints 'Hello, World!' and run it to verify."
    
    # Sample plan JSON that would be returned by the LLM
    plan_json = """[
        {
            "type": "create_file",
            "file_path": "hello.py"
        },
        {
            "type": "write_code",
            "file_path": "hello.py",
            "code": "print('Hello, World!')"
        },
        {
            "type": "run_command",
            "command": "python hello.py"
        },
        {
            "type": "run_command_and_check",
            "command": "python hello.py",
            "expected_output": "Hello, World!"
        }
    ]"""
    
    # Sample LLM response with the JSON embedded
    llm_response = f"""I've analyzed your request and broken it down into the following steps:

```json
{plan_json}
```

These steps will:
1. Create a hello.py file
2. Write code to print 'Hello, World!'
3. Run the script
4. Run the script again and verify the output is 'Hello, World!'
"""
    
    return {
        "query": plan_query,
        "json": plan_json,
        "response": llm_response
    } 