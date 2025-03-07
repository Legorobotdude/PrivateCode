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