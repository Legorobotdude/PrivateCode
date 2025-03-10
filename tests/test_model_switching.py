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
            
            # Mock input to return 'y' to any confirmation prompts
            mock_input.return_value = 'y'
            
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
            
            # Mock input to return 'y' to any confirmation prompts
            mock_input.return_value = 'y'
            
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
            user_input = "model: list"  # Use "list" explicitly as it's the special case in the code
            
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
            
            # Mock user input for both model selection and confirmation
            # First call returns the model selection, second call returns the confirmation
            mock_input.side_effect = ["model2", "y"]
            
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

    @patch('requests.get')
    @patch('builtins.input')
    def test_handle_model_query_with_unavailable_model(self, mock_input, mock_get):
        """Test handle_model_query when trying to switch to an unavailable model."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set up test
            conversation_history = []
            user_input = "model: unavailable_model"
            
            # Mock the API response for available models that doesn't include the requested model
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "model1"},
                    {"name": "model2"}
                ]
            }
            mock_get.return_value = mock_response
            
            # Mock input to first respond 'y' to the warning about unavailable model
            # and then 'y' to confirm the change
            mock_input.side_effect = ['y', 'y']
            
            # Call the function
            code_assistant.handle_model_query(user_input, conversation_history)
            
            # Check that the model was changed despite being unavailable
            # This tests the case where the user wants to try a model that might be available
            # but not yet loaded/pulled
            assert code_assistant.CURRENT_MODEL == "unavailable_model", "Model should be changed despite being unavailable"
            
            # Check that the conversation history was updated with model change
            assert len(conversation_history) == 1
            assert "unavailable_model" in conversation_history[0]["content"]
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model
    
    @patch('requests.get')
    @patch('builtins.input')
    def test_handle_model_query_reject_unavailable_model(self, mock_input, mock_get):
        """Test handle_model_query when user rejects switching to an unavailable model."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set up test
            conversation_history = []
            user_input = "model: unavailable_model"
            
            # Mock the API response for available models that doesn't include the requested model
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "model1"},
                    {"name": "model2"}
                ]
            }
            mock_get.return_value = mock_response
            
            # Mock input to respond 'n' when warned about unavailable model
            mock_input.return_value = 'n'
            
            # Call the function
            code_assistant.handle_model_query(user_input, conversation_history)
            
            # Check that the model was not changed
            assert code_assistant.CURRENT_MODEL == original_model, "Model should not change when user rejects unavailable model"
            
            # Check that the conversation history was not updated
            assert len(conversation_history) == 0
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model
    
    @patch('requests.get')
    @patch('builtins.print')
    def test_check_ollama_connection_unavailable_default_model(self, mock_print, mock_get):
        """Test check_ollama_connection when the default model is not in available models."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set a model that won't be in the available models list
            code_assistant.CURRENT_MODEL = "nonexistent_model"
            
            # Mock the API response with available models
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "models": [
                    {"name": "model1"},
                    {"name": "model2"}
                ]
            }
            mock_get.return_value = mock_response
            
            # Call the function
            result = code_assistant.check_ollama_connection()
            
            # Should still connect successfully even though default model isn't available
            assert result is True
            
            # Should print available models
            available_models_printed = any("Available models: model1, model2" in str(args) 
                                        for args, _ in mock_print.call_args_list)
            assert available_models_printed, "Should print available models"
            
            # Should NOT switch model automatically - we're only checking connection
            assert code_assistant.CURRENT_MODEL == "nonexistent_model", "Should not change current model"
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model
    
    @patch('requests.post')
    @patch('builtins.print')
    @patch('code_assistant.get_available_models')
    def test_get_ollama_response_with_unavailable_model(self, mock_get_available_models, mock_print, mock_post):
        """Test get_ollama_response when the selected model is not available."""
        # Mock a 404 response for model not found
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        mock_response.text = "Model not found"
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found", response=mock_response)
        mock_post.return_value = mock_response
        
        # Make sure get_available_models returns an empty list to prevent fallback
        mock_get_available_models.return_value = []

        # Create a simple history
        history = [{"role": "user", "content": "Hello, how are you?"}]

        # Get response with non-existent model
        response = code_assistant.get_ollama_response(history, model="nonexistent_model")

        # Check error message
        assert "Model 'nonexistent_model' not found" in response
        assert "pull the model" in response.lower()

        # Check appropriate warning was printed
        model_not_found_printed = any("Model 'nonexistent_model' not found" in str(args)
                                     for args, _ in mock_print.call_args_list)
        assert model_not_found_printed, "Should print model not found message"
    
    @patch('requests.post')
    @patch('requests.get')
    @patch('builtins.input')
    def test_handle_model_query_server_connection_error(self, mock_input, mock_get, mock_post):
        """Test handle_model_query when Ollama server is unreachable."""
        # Save original model
        original_model = code_assistant.CURRENT_MODEL
        
        try:
            # Set up test
            conversation_history = []
            user_input = "model: new_model"
            
            # Mock a connection error when checking available models
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Mock input to respond 'y' when asked to proceed without checking
            # and 'y' when asked to confirm the change
            mock_input.side_effect = ['y', 'y']
            
            # Call the function
            code_assistant.handle_model_query(user_input, conversation_history)
            
            # Check that model was changed despite connection error
            assert code_assistant.CURRENT_MODEL == "new_model", "Model should change if user confirms despite connection error"
            
            # Now test using this model when the server is still down
            # Mock post to also raise connection error
            mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")
            
            # Try to get a response with the new model
            history = [{"role": "user", "content": "Test query"}]
            response = code_assistant.get_ollama_response(history)
            
            # Verify error handling
            assert "Connection error" in response
            
        finally:
            # Restore original model
            code_assistant.CURRENT_MODEL = original_model

    @patch('requests.post')
    @patch('code_assistant.get_available_models')
    def test_default_model_fallback_behavior(self, mock_get_models, mock_post):
        """Test what happens when the default model is unavailable during startup."""
        # Save original DEFAULT_MODEL and CURRENT_MODEL
        original_default = code_assistant.DEFAULT_MODEL
        original_current = code_assistant.CURRENT_MODEL
        
        try:
            # Set a non-existent default model
            code_assistant.DEFAULT_MODEL = "nonexistent_default_model"
            code_assistant.CURRENT_MODEL = "nonexistent_default_model"
            
            # Mock get_available_models to return an empty list to prevent fallback behavior
            mock_get_models.return_value = []
            
            # Mock 404 response for model not found
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.reason = "Not Found"
            mock_response.text = "Model not found"
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "404 Not Found", response=mock_response)
            mock_post.return_value = mock_response
            
            # Create a simple history
            history = [{"role": "user", "content": "Hello, how are you?"}]
            
            # Get response with the current (non-existent) model
            response = code_assistant.get_ollama_response(history)
            
            # Check error message format 
            assert "Model 'nonexistent_default_model' not found" in response
            assert "Pull the model" in response
            
            # Verify that CURRENT_MODEL is unchanged - the code doesn't auto-switch models
            assert code_assistant.CURRENT_MODEL == "nonexistent_default_model"
            
            # The most important assertion: the API request still used the non-existent model
            # rather than automatically falling back to a different model
            call_args = mock_post.call_args[1]['json']
            assert call_args['model'] == "nonexistent_default_model"
            
        finally:
            # Restore original values
            code_assistant.DEFAULT_MODEL = original_default
            code_assistant.CURRENT_MODEL = original_current 