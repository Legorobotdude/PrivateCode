"""
Extended tests for web search functionality in the code assistant.

This test suite provides more comprehensive tests for web search capabilities,
focusing on:
1. Web search content extraction
2. Mock external API calls
3. Error handling and timeout scenarios
4. Search result processing and formatting
"""
import pytest
from unittest.mock import patch, MagicMock, call
import requests
from bs4 import BeautifulSoup
import json
import re
import code_assistant
from tests.utils import create_mock_ollama_response


class TestWebSearchExtended:
    """Extended tests for the web search functionality."""

    @patch('requests.get')
    def test_fetch_url_content_html_truncation(self, mock_get):
        """Test that HTML content is properly truncated when it exceeds the maximum length."""
        # Create a very long HTML content
        long_content = '<html><body>' + '<p>This is a test paragraph.</p>' * 1000 + '</body></html>'
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'text/html'}
        mock_response.text = long_content
        mock_get.return_value = mock_response
        
        content = code_assistant.fetch_url_content("https://example.com/longpage")
        
        # Check that content is truncated
        assert len(content) <= code_assistant.MAX_URL_CONTENT_LENGTH + len("... [content truncated]")
        assert "... [content truncated]" in content
        assert "This is a test paragraph." in content

    @patch('requests.get')
    def test_fetch_url_content_nonhtml(self, mock_get):
        """Test fetching non-HTML content like JSON."""
        json_content = json.dumps({"key": "value", "list": [1, 2, 3]})
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'Content-Type': 'application/json'}
        mock_response.text = json_content
        mock_get.return_value = mock_response
        
        content = code_assistant.fetch_url_content("https://example.com/api/data.json")
        
        # Check that JSON content is preserved
        assert '{"key": "value", "list": [1, 2, 3]}' in content

    @patch('requests.get')
    def test_fetch_url_content_various_errors(self, mock_get):
        """Test various HTTP error scenarios when fetching URL content."""
        test_cases = [
            (403, "forbidden"),
            (429, "Too many requests"),
            (500, "internal error"),
            (503, "Service Unavailable")
        ]
        
        for status_code, expected_text in test_cases:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_get.return_value = mock_response
            
            content = code_assistant.fetch_url_content(f"https://example.com/error{status_code}")
            assert "Failed to fetch" in content
            assert str(status_code) in content

    @patch('requests.get')
    def test_fetch_url_content_request_exceptions(self, mock_get):
        """Test handling of various request exceptions."""
        # Test Timeout exception
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        content = code_assistant.fetch_url_content("https://example.com/exception")
        assert "Failed to fetch" in content
        assert "timed out" in content.lower()
        
        # Test ConnectionError exception
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        content = code_assistant.fetch_url_content("https://example.com/exception")
        assert "Failed to fetch" in content
        assert "connection" in content.lower()
        
        # Test TooManyRedirects exception
        mock_get.side_effect = requests.exceptions.TooManyRedirects("Exceeded 30 redirects")
        content = code_assistant.fetch_url_content("https://example.com/exception")
        assert "Failed to fetch" in content
        assert "redirect" in content.lower()
        
        # Test InvalidURL exception
        mock_get.side_effect = requests.exceptions.InvalidURL("Invalid URL")
        content = code_assistant.fetch_url_content("https://example.com/exception")
        assert "Failed to fetch" in content
        assert "Request" in content

    @patch('requests.get')
    def test_duckduckgo_search_html_parsing(self, mock_get):
        """Test DuckDuckGo search with various HTML structures."""
        # Create a more complex HTML with different result formats
        mock_html = """
        <html>
            <body>
                <div class="result">
                    <h2 class="result__title"><a href="/url?q=https://example.com/page1">Example Page 1</a></h2>
                    <div class="result__snippet">This is the first result snippet.</div>
                    <div class="result__url">example.com/page1</div>
                </div>
                <div class="result">
                    <h2 class="result__title"><a href="/url?uddg=https%3A%2F%2Fexample.com%2Fpage2">Example Page 2</a></h2>
                    <div class="result__snippet">This is the second result snippet.</div>
                    <!-- No URL element to test fallback -->
                </div>
                <div class="result">
                    <!-- Malformed result with no title -->
                    <div class="result__snippet">This should be skipped.</div>
                    <div class="result__url">example.com/skip</div>
                </div>
                <div class="result">
                    <h2 class="result__title"><a href="https://example.com/page3">Direct Link</a></h2>
                    <div class="result__snippet">This has a direct link.</div>
                    <div class="result__url">example.com/page3</div>
                </div>
            </body>
        </html>
        """
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response
        
        results = code_assistant.duckduckgo_search("test complex query", num_results=5)
        
        assert len(results) >= 2  # Should get at least 2 valid results
        assert results[0]['title'] == "Example Page 1"
        assert results[1]['title'] == "Example Page 2"
        # Check URL extraction - the URL format may vary, just check for presence of relevant parts
        if 'url' in results[1]:
            assert "example.com" in results[1]['url'] or "example.com" in results[1]['url'].replace('%2F', '/').replace('%3A', ':')

    @patch('requests.get')
    def test_duckduckgo_search_num_results_limit(self, mock_get):
        """Test that DuckDuckGo search respects the num_results limit."""
        # Create HTML with many results
        mock_html = "<html><body>"
        for i in range(10):
            mock_html += f"""
                <div class="result">
                    <h2 class="result__title"><a href="https://example.com/page{i}">Result {i}</a></h2>
                    <div class="result__snippet">This is result {i}.</div>
                    <div class="result__url">example.com/page{i}</div>
                </div>
            """
        mock_html += "</body></html>"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = mock_html
        mock_get.return_value = mock_response
        
        # Test with different limits
        results_default = code_assistant.duckduckgo_search("test query")
        assert len(results_default) == code_assistant.MAX_SEARCH_RESULTS
        
        results_custom = code_assistant.duckduckgo_search("test query", num_results=3)
        assert len(results_custom) == 3
        
        results_large = code_assistant.duckduckgo_search("test query", num_results=8)
        assert len(results_large) == 8

    @patch('code_assistant.duckduckgo_search')
    @patch('code_assistant.get_ollama_response')
    def test_handle_search_query(self, mock_get_ollama_response, mock_duckduckgo_search):
        """Test the handle_search_query function for processing and formatting search results."""
        # Mock search results
        mock_search_results = [
            {
                'title': 'Python Requests Documentation',
                'snippet': 'The requests module allows you to send HTTP requests using Python.',
                'url': 'https://docs.python-requests.org/en/latest/'
            },
            {
                'title': 'HTTP Status Codes',
                'snippet': 'Common HTTP status codes and their meanings.',
                'url': 'https://developer.mozilla.org/en-US/docs/Web/HTTP/Status'
            }
        ]
        mock_duckduckgo_search.return_value = mock_search_results
        
        # Mock the AI response
        mock_ollama_response = create_mock_ollama_response("This is a response about web search.")
        mock_get_ollama_response.return_value = mock_ollama_response
        
        # Create a conversation history
        conversation_history = []
        
        # Call the function
        code_assistant.handle_search_query("Search: Python requests library", conversation_history)
        
        # Check that the conversation history is updated correctly
        assert len(conversation_history) >= 1  # At least the user message should be there
        
        # Check the content of the user message
        user_message = conversation_history[0]['content']
        assert "Web Search Query: Python requests library" in user_message
        assert "Python Requests Documentation" in user_message
        assert "HTTP Status Codes" in user_message
        
        # Verify that the mock was called with expected parameters
        mock_duckduckgo_search.assert_called_once_with("Python requests library")

    @patch('code_assistant.duckduckgo_search')
    @patch('code_assistant.get_ollama_response')
    def test_handle_search_query_no_results(self, mock_get_ollama_response, mock_duckduckgo_search):
        """Test handle_search_query when no search results are found."""
        # Mock empty search results
        mock_duckduckgo_search.return_value = []
        
        # Mock the AI response
        mock_ollama_response = create_mock_ollama_response("This is a response with no search results.")
        mock_get_ollama_response.return_value = mock_ollama_response
        
        # Create a conversation history
        conversation_history = []
        
        # Call the function
        code_assistant.handle_search_query("Search: nonexistent topic", conversation_history)
        
        # Check the conversation history
        assert len(conversation_history) >= 1  # At least the user message should be there
        
        # Check the user message doesn't have search results section
        user_message = conversation_history[0]['content']
        assert "Web Search Query: nonexistent topic" in user_message
        assert "Search Results:" not in user_message

    def test_extract_search_query(self):
        """Test the extract_search_query function with various input formats."""
        # Test with "Search:" prefix
        assert code_assistant.extract_search_query("Search: Python requests") == "Python requests"
        
        # Test with "Search " prefix
        assert code_assistant.extract_search_query("Search Python async/await") == "Python async/await"
        
        # Test with mixed case
        assert code_assistant.extract_search_query("sEaRcH: Machine learning") == "Machine learning"
        
        # Test with extra spaces
        assert code_assistant.extract_search_query("Search:    Data structures") == "Data structures"
        
        # Test without search prefix (should return the original query)
        assert code_assistant.extract_search_query("Regular query") == "Regular query"

    def test_is_search_query(self):
        """Test the is_search_query function."""
        # Test positive cases
        assert code_assistant.is_search_query("Search: Python")
        assert code_assistant.is_search_query("search: Python")
        assert code_assistant.is_search_query("SEARCH: Python")
        assert code_assistant.is_search_query("Search Python")
        
        # Test negative cases
        assert not code_assistant.is_search_query("Python search: term")
        assert not code_assistant.is_search_query("Python search term")
        assert not code_assistant.is_search_query("searching for Python") 