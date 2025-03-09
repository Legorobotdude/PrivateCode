"""
Tests for Ollama API interaction in the code assistant.
"""
import pytest
from unittest.mock import patch, MagicMock
import requests
import json
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
        
        # Reset the mock for the next test
        mock_post.reset_mock()
        
        # Mock an API error
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.json.return_value = {"error": "API Error"}
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error", response=mock_response)
        
        # The implementation might handle errors gracefully instead of raising exceptions
        response = code_assistant.get_ollama_response(history, model="codellama")
        assert "Error" in response, "Response should contain error message for API errors"
        assert "internal error" in response.lower(), "Response should indicate server error type"
        
        # Reset the mock for the next test
        mock_post.reset_mock()
        mock_post.side_effect = None
        
        # Mock a connection error
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")
        response = code_assistant.get_ollama_response(history, model="codellama")
        # Check for the actual message format
        assert "Request failed" in response, "Response should indicate request failure"
        assert "RequestException" in response, "Response should indicate request exception type"
        assert "Connection error" in response, "Response should indicate the connection error"
    
    @patch('requests.post')
    def test_get_ollama_response_timeout(self, mock_post):
        """Test that the get_ollama_response function handles timeouts properly."""
        # Mock a timeout exception
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
        
        history = [
            {"role": "user", "content": "Hello, can you help me with some code?"}
        ]
        response = code_assistant.get_ollama_response(history, model="codellama", timeout=10)
        
        assert "timed out" in response.lower(), "Response should indicate timeout"
        assert "10 seconds" in response, "Response should include the timeout value"
    
    @patch('requests.post')
    def test_get_ollama_response_connection_error(self, mock_post):
        """Test that the get_ollama_response function handles connection errors properly."""
        # Mock a connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
        
        history = [
            {"role": "user", "content": "Hello, can you help me with some code?"}
        ]
        response = code_assistant.get_ollama_response(history, model="codellama")
        
        assert "Connection error" in response, "Response should indicate connection error"
        with patch('builtins.print') as mock_print:
            code_assistant.get_ollama_response(history, model="codellama")
            suggestion_printed = any("still running" in str(args) for args, _ in mock_print.call_args_list)
            assert suggestion_printed, "Should print a suggestion to check if Ollama is still running"
    
    @patch('requests.post')
    def test_get_ollama_response_http_errors(self, mock_post):
        """Test that the get_ollama_response function handles different HTTP errors properly."""
        history = [
            {"role": "user", "content": "Hello, can you help me with some code?"}
        ]
        
        # Test 404 Not Found (model not found)
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        mock_response.text = "Model not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found", response=mock_response)
        mock_post.return_value = mock_response
        
        response = code_assistant.get_ollama_response(history, model="nonexistent_model")
        assert "Model 'nonexistent_model' not found" in response, "Response should indicate model not found"
        assert "pull the model" in response, "Response should suggest pulling the model"
        
        # Test 400 Bad Request
        mock_response.status_code = 400
        mock_response.reason = "Bad Request"
        mock_response.text = "Bad request"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "400 Bad Request", response=mock_response)
        
        response = code_assistant.get_ollama_response(history, model="codellama")
        assert "Bad request" in response, "Response should indicate bad request"
        
        # Test 500 Internal Server Error
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_response.text = "Server error"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Internal Server Error", response=mock_response)
        
        response = code_assistant.get_ollama_response(history, model="codellama")
        assert "internal error" in response.lower(), "Response should indicate server error"
        
        with patch('builtins.print') as mock_print:
            code_assistant.get_ollama_response(history, model="codellama")
            restart_printed = any("restart" in str(args).lower() for args, _ in mock_print.call_args_list)
            assert restart_printed, "Should print a suggestion to restart the Ollama server"
    
    @patch('requests.post')
    def test_get_ollama_response_json_decode_error(self, mock_post):
        """Test that the get_ollama_response function handles JSON decode errors properly."""
        # Mock a successful response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Not valid JSON"
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "Not valid JSON", 0)
        mock_post.return_value = mock_response
        
        history = [
            {"role": "user", "content": "Hello, can you help me with some code?"}
        ]
        response = code_assistant.get_ollama_response(history, model="codellama")
        
        assert "Failed to parse JSON" in response, "Response should indicate JSON parsing error"
        assert "Invalid JSON" in response, "Response should include the specific error message"
    
    @patch('requests.post')
    def test_get_ollama_response_empty_content(self, mock_post):
        """Test that the get_ollama_response function handles empty responses properly."""
        # Mock a successful response with empty content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": ""  # Empty content
            }
        }
        mock_post.return_value = mock_response
        
        history = [
            {"role": "user", "content": "Hello, can you help me with some code?"}
        ]
        response = code_assistant.get_ollama_response(history, model="codellama")
        
        assert response == "", "Response should be empty string when API returns empty content"
    
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