#!/usr/bin/env python3
"""
Test script for the timeout functionality in the code assistant.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import requests

# Add the parent directory to the path so we can import code_assistant
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import code_assistant


class TestTimeout(unittest.TestCase):
    """Test the timeout functionality."""

    def setUp(self):
        """Set up the test environment."""
        # Save original values
        self.original_timeout = code_assistant.DEFAULT_TIMEOUT

    def tearDown(self):
        """Clean up after the test."""
        # Restore original values
        code_assistant.DEFAULT_TIMEOUT = self.original_timeout

    def test_set_timeout_valid(self):
        """Test setting a valid timeout value."""
        with patch('builtins.print') as mock_print:
            # Set timeout to a valid value
            result = code_assistant.set_timeout("120")
            self.assertEqual(result, 120)
            self.assertEqual(code_assistant.DEFAULT_TIMEOUT, 120)
            # Check that appropriate message was printed
            mock_print.assert_called_with(f"{code_assistant.Fore.GREEN}Timeout set to 120 seconds.{code_assistant.Style.RESET_ALL}")

    def test_set_timeout_invalid_format(self):
        """Test setting an invalid timeout value (non-integer)."""
        # Set original timeout
        code_assistant.DEFAULT_TIMEOUT = 60
        
        with patch('builtins.print') as mock_print:
            # Set timeout to an invalid value
            result = code_assistant.set_timeout("abc")
            self.assertEqual(result, 60)  # Should return the original value
            self.assertEqual(code_assistant.DEFAULT_TIMEOUT, 60)  # Should not change
            # Check that error message was printed
            mock_print.assert_called_with(f"{code_assistant.Fore.YELLOW}Invalid timeout value. Please provide a number.{code_assistant.Style.RESET_ALL}")

    def test_set_timeout_negative(self):
        """Test setting a negative timeout value."""
        # Set original timeout
        code_assistant.DEFAULT_TIMEOUT = 60
        
        with patch('builtins.print') as mock_print:
            # Set timeout to a negative value
            result = code_assistant.set_timeout("-10")
            self.assertEqual(result, 60)  # Should return the original value
            self.assertEqual(code_assistant.DEFAULT_TIMEOUT, 60)  # Should not change
            # Check that error message was printed
            mock_print.assert_called_with(f"{code_assistant.Fore.YELLOW}Timeout must be a positive integer. Using current value of 60.{code_assistant.Style.RESET_ALL}")

    def test_get_ollama_response_timeout(self):
        """Test that get_ollama_response uses the custom timeout value."""
        # Mock the requests.post method to avoid actual API calls
        with patch('requests.post') as mock_post:
            # Configure the mock to simulate a successful request
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"message": {"content": "Test response"}}
            mock_post.return_value = mock_response
            
            # Test with default timeout
            code_assistant.DEFAULT_TIMEOUT = 60
            code_assistant.get_ollama_response([{"role": "user", "content": "Hello"}])
            # Check that requests.post was called with the default timeout
            mock_post.assert_called_with(code_assistant.OLLAMA_API_URL, 
                                        json={'model': code_assistant.CURRENT_MODEL, 
                                              'messages': [{"role": "user", "content": "Hello"}], 
                                              'stream': False}, 
                                        timeout=60)
            
            # Test with custom timeout
            code_assistant.DEFAULT_TIMEOUT = 120
            code_assistant.get_ollama_response([{"role": "user", "content": "Hello"}])
            # Check that requests.post was called with the updated timeout
            mock_post.assert_called_with(code_assistant.OLLAMA_API_URL, 
                                        json={'model': code_assistant.CURRENT_MODEL, 
                                              'messages': [{"role": "user", "content": "Hello"}], 
                                              'stream': False}, 
                                        timeout=120)
            
            # Test with override timeout parameter
            code_assistant.get_ollama_response([{"role": "user", "content": "Hello"}], timeout=180)
            # Check that requests.post was called with the override timeout
            mock_post.assert_called_with(code_assistant.OLLAMA_API_URL, 
                                        json={'model': code_assistant.CURRENT_MODEL, 
                                              'messages': [{"role": "user", "content": "Hello"}], 
                                              'stream': False}, 
                                        timeout=180)

    def test_timeout_error_message(self):
        """Test that timeout error message includes the timeout value."""
        # Set a timeout value
        code_assistant.DEFAULT_TIMEOUT = 90
        
        # Mock the requests.post method to simulate a timeout
        with patch('requests.post') as mock_post, patch('builtins.print') as mock_print:
            # Configure the mock to raise a Timeout exception
            mock_post.side_effect = requests.exceptions.Timeout("Request timed out")
            
            # Call get_ollama_response
            result = code_assistant.get_ollama_response([{"role": "user", "content": "Hello"}])
            
            # Check that the error message contains the timeout value
            self.assertIn("timed out after 90 seconds", result)
            # Check that the error message was printed
            mock_print.assert_any_call(f"{code_assistant.Fore.RED}Request to Ollama API timed out after 90 seconds. The model might be taking too long to respond.{code_assistant.Style.RESET_ALL}")


if __name__ == "__main__":
    unittest.main() 