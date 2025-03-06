"""
Tests for model switching functionality in the code assistant.
"""
import pytest
from unittest.mock import patch, MagicMock
import requests
import code_assistant
from tests.utils import mock_requests_post, create_mock_ollama_response

class TestModelSwitching:
    """Tests for the model switching functionality."""
    
    def test_is_model_query(self):
        """Test the is_model_query function."""
        # Test various model query formats
        assert code_assistant.is_model_query("model: llama3")
        assert code_assistant.is_model_query("MODEL: codellama")
        assert code_assistant.is_model_query("model llama3")
        assert code_assistant.is_model_query("use model: mistral")
        assert code_assistant.is_model_query("use model codellama")
        
        # Test non-model queries
        assert not code_assistant.is_model_query("How do I use a model?")
        assert not code_assistant.is_model_query("What is the best model?")
        assert not code_assistant.is_model_query("search: model comparison")
    
    def test_extract_model_query(self):
        """Test the extract_model_query function."""
        # Test various model query formats
        assert code_assistant.extract_model_query("model: llama3") == "llama3"
        assert code_assistant.extract_model_query("MODEL: codellama") == "codellama"
        assert code_assistant.extract_model_query("model llama3") == "llama3"
        assert code_assistant.extract_model_query("use model: mistral") == "mistral"
        assert code_assistant.extract_model_query("use model codellama") == "codellama"
        
        # Test with extra text
        assert code_assistant.extract_model_query("model: llama3 for my project") == "llama3 for my project"
    
    @patch('requests.post')
    def test_get_ollama_response_model_selection(self, mock_post):
        """Test that get_ollama_response uses the correct model."""
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
        
        # Test with explicit model parameter
        code_assistant.get_ollama_response(history, model="explicit_model")
        call_args = mock_post.call_args[1]['json']
        assert call_args['model'] == "explicit_model", "Should use explicitly provided model"
        
        # Test with CURRENT_MODEL
        original_model = code_assistant.CURRENT_MODEL
        try:
            code_assistant.CURRENT_MODEL = "current_test_model"
            code_assistant.get_ollama_response(history)
            call_args = mock_post.call_args[1]['json']
            assert call_args['model'] == "current_test_model", "Should use CURRENT_MODEL when no model is specified"
        finally:
            # Restore the original model
            code_assistant.CURRENT_MODEL = original_model
    
    @patch('requests.get')
    @patch('builtins.input')
    def test_handle_model_query_with_specific_model(self, mock_input, mock_get):
        """Test handle_model_query with a specific model name."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set up test
            conversation_history = []
            user_input = "model: test_model"
            
            # Call the function
            code_assistant.handle_model_query(user_input, conversation_history)
            
            # Check that the model was changed
            assert code_assistant.CURRENT_MODEL == "test_model", "Model should be changed to test_model"
            
            # Check that the conversation history was updated
            assert len(conversation_history) == 1
            assert conversation_history[0]["role"] == "system"
            assert "test_model" in conversation_history[0]["content"]
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model
    
    @patch('requests.get')
    @patch('builtins.input')
    def test_handle_model_query_with_quoted_model(self, mock_input, mock_get):
        """Test handle_model_query with a model name in quotes."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set up test
            conversation_history = []
            user_input = "model: 'quoted_test_model'"
            
            # Call the function
            code_assistant.handle_model_query(user_input, conversation_history)
            
            # Check that the model was changed
            assert code_assistant.CURRENT_MODEL == "quoted_test_model", "Model should be changed to quoted_test_model"
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model
    
    @patch('requests.get')
    @patch('builtins.input')
    def test_handle_model_query_with_available_models(self, mock_input, mock_get):
        """Test handle_model_query when listing available models."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set up test
            conversation_history = []
            user_input = "model:"
            
            # Mock the API response for available models
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "model1"},
                    {"name": "model2"},
                    {"name": "model3"}
                ]
            }
            mock_get.return_value = mock_response
            
            # Mock user input to select a model
            mock_input.return_value = "model2"
            
            # Call the function
            code_assistant.handle_model_query(user_input, conversation_history)
            
            # Check that the model was changed
            assert code_assistant.CURRENT_MODEL == "model2", "Model should be changed to model2"
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model
    
    @patch('requests.get')
    @patch('builtins.input')
    def test_handle_model_query_with_empty_input(self, mock_input, mock_get):
        """Test handle_model_query when user provides empty input for model selection."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set up test
            conversation_history = []
            user_input = "model:"
            
            # Mock the API response for available models
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "model1"},
                    {"name": "model2"}
                ]
            }
            mock_get.return_value = mock_response
            
            # Mock user input to be empty
            mock_input.return_value = ""
            
            # Call the function
            code_assistant.handle_model_query(user_input, conversation_history)
            
            # Check that the model was not changed
            assert code_assistant.CURRENT_MODEL == original_model, "Model should not change with empty input"
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model 