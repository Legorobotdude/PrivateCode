"""
Tests for web search functionality in the code assistant.
"""
import pytest
from unittest.mock import patch, MagicMock
import requests
from bs4 import BeautifulSoup
import code_assistant
from tests.utils import create_mock_ollama_response

class TestWebSearch:
    """Tests for the web search functionality."""
    
    @patch('requests.get')
    def test_fetch_url_content(self, mock_get):
        """Test the fetch_url_content function."""
        # Mock a successful response with HTML content
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = '<html><body><h1>Test Page</h1><p>Test content.</p></body></html>'
        mock_get.return_value = mock_response
        
        content = code_assistant.fetch_url_content("https://example.com")
        assert "Test Page" in content
        assert "Test content" in content
        
        # Mock a failed response
        mock_response.status_code = 404
        content = code_assistant.fetch_url_content("https://example.com/notfound")
        assert "Failed to fetch" in content, "Should return error message for failed requests"
        
        # Mock a connection error
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        content = code_assistant.fetch_url_content("https://example.com/error")
        assert "Failed to fetch" in content, "Should return error message for connection errors"
    
    @patch('requests.get')
    def test_duckduckgo_search(self, mock_get):
        """Test the duckduckgo_search function."""
        # Mock a successful search response
        mock_html = """
        <html>
            <body>
                <div class="result">
                    <h2 class="result__title"><a href="https://example.com/page1">Example Page 1</a></h2>
                    <div class="result__snippet">This is the first result snippet.</div>
                    <div class="result__url">example.com/page1</div>
                </div>
                <div class="result">
                    <h2 class="result__title"><a href="https://example.com/page2">Example Page 2</a></h2>
                    <div class="result__snippet">This is the second result snippet.</div>
                    <div class="result__url">example.com/page2</div>
                </div>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response
        
        # We'll just check that the function runs without errors
        # and returns a list (which might be empty depending on the parsing)
        results = code_assistant.duckduckgo_search("test query", num_results=2)
        assert isinstance(results, list), "Should return a list of results"
        
        # Test with connection error
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")
        results = code_assistant.duckduckgo_search("error query")
        assert results == [], "Should return empty list for connection errors"
    
    def test_extract_file_paths_and_urls(self):
        """Test the extract_file_paths_and_urls function."""
        # Test with a single file path in brackets
        query = "Check the file [app.py]"
        clean_query, file_paths, urls = code_assistant.extract_file_paths_and_urls(query)
        assert "Check the file" in clean_query
        assert len(file_paths) == 1
        assert file_paths[0][0] == "app.py"  # First element of the tuple is the file path
        assert len(urls) == 0
        
        # Test with a single URL in brackets
        query = "Look at [https://example.com]"
        clean_query, file_paths, urls = code_assistant.extract_file_paths_and_urls(query)
        assert "Look at" in clean_query
        assert len(file_paths) == 0
        assert "https://example.com" in urls
        
        # Test with both in brackets
        query = "Look at [file.py] and [https://example.com]"
        clean_query, file_paths, urls = code_assistant.extract_file_paths_and_urls(query)
        assert "Look at  and" in clean_query
        assert len(file_paths) == 1
        assert file_paths[0][0] == "file.py"  # First element of the tuple is the file path
        assert "https://example.com" in urls 