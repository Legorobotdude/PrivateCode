"""
Tests for Ollama API interaction in the code assistant.
"""
import pytest
from unittest.mock import patch, MagicMock
import requests
import code_assistant
from tests.utils import mock_requests_post, create_mock_ollama_response

class TestOllamaAPI:
    """Tests for the Ollama API interaction."""
    
    @patch('requests.get')
    def test_check_ollama_connection(self, mock_get):
        """Test the check_ollama_connection function."""
        # Mock a successful connection
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "codellama"},
                {"name": "llama2"}
            ]
        }
        mock_get.return_value = mock_response
        
        result = code_assistant.check_ollama_connection()
        assert result is True, "Connection check should succeed with valid response"
        
        # Mock a failed connection
        mock_response.status_code = 500
        result = code_assistant.check_ollama_connection()
        assert result is False, "Connection check should fail with invalid response"
        
        # Mock a connection error
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        result = code_assistant.check_ollama_connection()
        assert result is False, "Connection check should fail on exception"
    
    @patch('requests.post')
    def test_get_ollama_response(self, mock_post):
        """Test the get_ollama_response function."""
        # Mock a successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": "This is a response from the Ollama API"
            }
        }
        mock_post.return_value = mock_response
        
        history = [
            {"role": "user", "content": "Hello, can you help me with some code?"}
        ]
        response = code_assistant.get_ollama_response(history, model="codellama")
        assert response == "This is a response from the Ollama API"
        
        # Check that the correct data was sent to the API
        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]['json']
        assert call_args['model'] == "codellama"
        assert len(call_args['messages']) == 1
        assert call_args['messages'][0]['role'] == "user"
        
        # Mock an API error
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "API Error"}
        
        # The implementation might handle errors gracefully instead of raising exceptions
        response = code_assistant.get_ollama_response(history, model="codellama")
        assert "Error" in response, "Response should contain error message for API errors"
        
        # Mock a connection error
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        response = code_assistant.get_ollama_response(history, model="codellama")
        assert "Error" in response, "Response should contain error message for connection errors"
    
    def test_query_classification(self):
        """Test the query classification functions."""
        # Test is_search_query
        assert code_assistant.is_search_query("search: how to use regex in python")
        assert code_assistant.is_search_query("SEARCH: python async tutorial")
        assert not code_assistant.is_search_query("Help me understand python")
        
        # Test is_edit_query
        assert code_assistant.is_edit_query("edit: app.py to fix the bug")
        assert code_assistant.is_edit_query("EDIT: utils/helpers.py to add logging")
        assert not code_assistant.is_edit_query("Can you help me fix a bug in app.py?")
        
        # Test is_run_query
        assert code_assistant.is_run_query("run: python -m pytest")
        assert code_assistant.is_run_query("RUN: ls -la")
        assert not code_assistant.is_run_query("How do I run pytest?")
        
        # Test is_model_query
        assert code_assistant.is_model_query("model: llama3")
        assert code_assistant.is_model_query("MODEL: codellama")
        assert code_assistant.is_model_query("use model: mistral")
        assert not code_assistant.is_model_query("What model should I use?")
        
        # Test extract_search_query
        assert code_assistant.extract_search_query("search: python generators") == "python generators"
        assert code_assistant.extract_search_query("Search: how to handle errors") == "how to handle errors"
        
        # Test extract_edit_query
        assert code_assistant.extract_edit_query("edit: app.py to add error handling") == "app.py to add error handling"
        assert code_assistant.extract_edit_query("Edit: models.py add a new class") == "models.py add a new class"
        
        # Test extract_run_query
        assert code_assistant.extract_run_query("run: python -m pytest") == "python -m pytest"
        assert code_assistant.extract_run_query("Run: ls -la") == "ls -la"
        
        # Test extract_model_query
        assert code_assistant.extract_model_query("model: llama3") == "llama3"
        assert code_assistant.extract_model_query("use model: mistral") == "mistral" 