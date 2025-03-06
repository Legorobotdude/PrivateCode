"""
Utility functions for testing the code assistant.
"""
import os
import requests
from unittest.mock import patch, MagicMock

def is_ollama_available():
    """Check if Ollama is running and accessible."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def create_test_file(directory, filename, content):
    """
    Create a test file with specified content.
    
    Args:
        directory (str): Directory where the file will be created
        filename (str): Name of the file
        content (str): Content to write to the file
    
    Returns:
        str: Full path to the created file
    """
    file_path = os.path.join(directory, filename)
    with open(file_path, 'w') as f:
        f.write(content)
    return file_path

def create_mock_ollama_response(content):
    """
    Create a mock response for the Ollama API.
    
    Args:
        content (str): The content of the response
    
    Returns:
        MagicMock: A mock response object
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": content
        }
    }
    return mock_response

def mock_requests_post(monkeypatch, return_value):
    """
    Mock the requests.post function.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        return_value: The value to return from the mock
    """
    def mock_post(*args, **kwargs):
        return return_value
    
    monkeypatch.setattr(requests, 'post', mock_post) 