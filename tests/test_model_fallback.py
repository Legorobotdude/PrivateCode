"""
Tests for model fallback functionality.

These tests check the model fallback behavior when the requested model is not available.
"""
import pytest
from unittest.mock import patch, MagicMock
import requests
import json
import code_assistant
from tests.utils import create_mock_ollama_response


class TestModelFallback:
    """Tests for model fallback functionality."""
    
    @patch('requests.post')
    @patch('requests.get')
    def test_automatic_fallback_to_available_model(self, mock_get, mock_post):
        """Test that the system automatically falls back to an available model.
        
        This tests the implementation where get_ollama_response tries
        an available model if the requested one is not found.
        """
        # Save original model values
        original_default = code_assistant.DEFAULT_MODEL
        original_current = code_assistant.CURRENT_MODEL
        
        try:
            # Configure a non-existent model
            code_assistant.CURRENT_MODEL = "my_missing_model"
            
            # Set up mock responses
            # First call to get available models
            available_models_response = MagicMock()
            available_models_response.status_code = 200
            available_models_response.json.return_value = {
                "models": [
                    {"name": "available_model1"},
                    {"name": "available_model2"}
                ]
            }
            mock_get.return_value = available_models_response
            
            # First call - 404 for the nonexistent model
            not_found_response = MagicMock()
            not_found_response.status_code = 404
            not_found_response.reason = "Not Found"
            not_found_response.text = "Model not found"
            not_found_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "404 Not Found", response=not_found_response)
            
            # Second call - 200 for the fallback model
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {
                "message": {
                    "content": "Response from fallback model"
                }
            }
            
            # Make the first call fail, but subsequent calls succeed
            mock_post.side_effect = [not_found_response, success_response]
            
            # Call the function explicitly with the nonexistent model
            history = [{"role": "user", "content": "Hello, how are you?"}]
            response = code_assistant.get_ollama_response(history, model="my_missing_model")
            
            # Should get a successful response
            assert "Response from fallback model" in response
            
            # The function should have been called twice
            assert mock_post.call_count == 2
            
            # The second call should use the first available model
            second_call_args = mock_post.call_args_list[1][1]['json']
            assert second_call_args['model'] == "available_model1"
            
            # History should include a system message about the fallback
            assert len(history) == 2
            assert history[1]["role"] == "system"
            assert "my_missing_model" in history[1]["content"]
            assert "available_model1" in history[1]["content"]
            
        finally:
            # Restore original values
            code_assistant.DEFAULT_MODEL = original_default
            code_assistant.CURRENT_MODEL = original_current
    
    @patch('requests.post')
    @patch('requests.get')
    @patch('builtins.print')
    def test_fallback_to_first_available_model(self, mock_print, mock_get, mock_post):
        """Test falling back to the first model from the available models list."""
        # Save original values
        original_default = code_assistant.DEFAULT_MODEL
        original_current = code_assistant.CURRENT_MODEL
        
        try:
            # Configure a non-existent model
            code_assistant.CURRENT_MODEL = "my_missing_model"
            
            # Mock the API response for available models
            mock_model_response = MagicMock()
            mock_model_response.status_code = 200
            mock_model_response.json.return_value = {
                "models": [
                    {"name": "available_model1"},
                    {"name": "available_model2"}
                ]
            }
            mock_get.return_value = mock_model_response
            
            # First call - 404 for the nonexistent model
            not_found_response = MagicMock()
            not_found_response.status_code = 404
            not_found_response.reason = "Not Found"
            not_found_response.text = "Model not found"
            not_found_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "404 Not Found", response=not_found_response)
            
            # Second call - 200 for the fallback model
            success_response = MagicMock()
            success_response.status_code = 200
            success_response.json.return_value = {
                "message": {
                    "content": "Response from first available model"
                }
            }
            
            # Make the first call fail, but subsequent calls succeed
            mock_post.side_effect = [not_found_response, success_response]
            
            # Call the function explicitly with the nonexistent model
            history = [{"role": "user", "content": "Hello, how are you?"}]
            response = code_assistant.get_ollama_response(history, model="my_missing_model")
            
            # Should get a successful response
            assert "Response from first available model" in response
            
            # The function should have been called twice
            assert mock_post.call_count == 2
            
            # The second call should use the first available model
            second_call_args = mock_post.call_args_list[1][1]['json']
            assert second_call_args['model'] == "available_model1"
            
            # Should print notification about the fallback
            fallback_printed = any("Falling back to available model" in str(args) 
                                 for args, _ in mock_print.call_args_list)
            assert fallback_printed, "Should notify user about fallback"
            
        finally:
            # Restore original values
            code_assistant.DEFAULT_MODEL = original_default
            code_assistant.CURRENT_MODEL = original_current
    
    @patch('requests.post')
    @patch('requests.get')
    @patch('builtins.print')
    def test_no_models_available_for_fallback(self, mock_print, mock_get, mock_post):
        """Test when no models are available for fallback."""
        # Save original values
        original_default = code_assistant.DEFAULT_MODEL
        original_current = code_assistant.CURRENT_MODEL
        
        try:
            # Configure a non-existent model
            code_assistant.CURRENT_MODEL = "nonexistent_model"
            
            # Mock the API response for no available models
            mock_model_response = MagicMock()
            mock_model_response.status_code = 200
            mock_model_response.json.return_value = {"models": []}
            mock_get.return_value = mock_model_response
            
            # Call to original model - 404 
            not_found_response = MagicMock()
            not_found_response.status_code = 404
            not_found_response.reason = "Not Found"
            not_found_response.text = "Model not found"
            not_found_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "404 Not Found", response=not_found_response)
            mock_post.return_value = not_found_response
            
            # Call the function explicitly with the nonexistent model
            history = [{"role": "user", "content": "Hello, how are you?"}]
            response = code_assistant.get_ollama_response(history, model="nonexistent_model")
            
            # Should return original error
            assert "Model 'nonexistent_model' not found" in response
            
            # Should print message about pulling models
            install_message_printed = any("pull a model" in str(args).lower() 
                                        for args, _ in mock_print.call_args_list)
            assert install_message_printed, "Should print message about pulling models"
            
            # Should suggest specific models
            models_suggested = any("llama3" in str(args) or "mistral" in str(args) 
                                 for args, _ in mock_print.call_args_list)
            assert models_suggested, "Should suggest specific models to pull"
            
        finally:
            # Restore original values
            code_assistant.DEFAULT_MODEL = original_default
            code_assistant.CURRENT_MODEL = original_current
    
    @patch('requests.post')
    def test_disable_fallback(self, mock_post):
        """Test that fallback can be disabled."""
        # Save original values
        original_default = code_assistant.DEFAULT_MODEL
        original_current = code_assistant.CURRENT_MODEL
        
        try:
            # Configure a non-existent model
            code_assistant.CURRENT_MODEL = "nonexistent_model"
            
            # First call - 404 for the nonexistent model
            not_found_response = MagicMock()
            not_found_response.status_code = 404
            not_found_response.reason = "Not Found"
            not_found_response.text = "Model not found"
            not_found_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                "404 Not Found", response=not_found_response)
            mock_post.return_value = not_found_response
            
            # Call the function with fallback disabled, explicitly with the nonexistent model
            history = [{"role": "user", "content": "Hello, how are you?"}]
            response = code_assistant.get_ollama_response(history, model="nonexistent_model", allow_fallback=False)
            
            # Should return error message about nonexistent model
            assert "Model 'nonexistent_model' not found" in response
            
            # The function should have been called only once
            assert mock_post.call_count == 1, "Should not attempt fallback when disabled"
            
        finally:
            # Restore original values
            code_assistant.DEFAULT_MODEL = original_default
            code_assistant.CURRENT_MODEL = original_current 