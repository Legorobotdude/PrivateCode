"""
Tests for file path and URL extraction functionality.
Focuses on edge cases and complex scenarios to ensure robust parsing.
"""
import pytest
import code_assistant

class TestPathUrlExtraction:
    """Test suite for extract_file_paths_and_urls function."""

    def test_basic_file_paths(self):
        """Test extraction of basic file paths."""
        test_cases = [
            # Simple file path
            (
                "Check [file.txt]",
                ["file.txt"],
                [],
                "Check"
            ),
            # Multiple file paths
            (
                "Compare [file1.py] with [file2.py]",
                ["file1.py", "file2.py"],
                [],
                "Compare  with"
            ),
            # File with extension but no path
            (
                "Look at [main.cpp]",
                ["main.cpp"],
                [],
                "Look at"
            ),
            # File without extension
            (
                "Show [Makefile]",
                ["Makefile"],
                [],
                "Show"
            )
        ]

        for query, expected_files, expected_urls, expected_clean in test_cases:
            clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
            assert clean_query == expected_clean
            assert len(file_items) == len(expected_files)
            assert all(item[0] == expected for item, expected in zip(file_items, expected_files))
            assert len(urls) == len(expected_urls)

    def test_file_paths_with_line_ranges(self):
        """Test extraction of file paths with line range specifications."""
        test_cases = [
            # Simple line range
            (
                "[file.py:10-20]",
                [("file.py", 10, 20)],
                []
            ),
            # Multiple files with line ranges
            (
                "Compare [file1.py:1-5] and [file2.py:10-15]",
                [("file1.py", 1, 5), ("file2.py", 10, 15)],
                []
            ),
            # Open-ended ranges
            (
                "[file.py:5-]",
                [("file.py", 5, None)],
                []
            ),
            # Single line
            (
                "[file.py:42]",
                [("file.py", 42, 43)],  # End is start+1 for single line
                []
            ),
            # Invalid line numbers
            (
                "[file.py:invalid]",
                [("file.py", None, None)],
                []
            )
        ]

        for query, expected_files, expected_urls in test_cases:
            clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
            assert len(file_items) == len(expected_files)
            for item, expected in zip(file_items, expected_files):
                assert item == expected
            assert len(urls) == len(expected_urls)

    def test_relative_paths(self):
        """Test extraction of relative file paths."""
        test_cases = [
            # Current directory
            (
                "[./file.txt]",
                ["./file.txt"],
                []
            ),
            # Parent directory
            (
                "[../file.txt]",
                ["../file.txt"],
                []
            ),
            # Nested paths
            (
                "[./src/components/Button.tsx]",
                ["./src/components/Button.tsx"],
                []
            ),
            # Multiple dots in path
            (
                "[../../project/file.txt]",
                ["../../project/file.txt"],
                []
            ),
            # Multiple slashes
            (
                "[src//nested//file.txt]",
                ["src//nested//file.txt"],
                []
            )
        ]

        for query, expected_files, expected_urls in test_cases:
            clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
            assert len(file_items) == len(expected_files)
            assert all(item[0] == expected for item, expected in zip(file_items, expected_files))
            assert len(urls) == len(expected_urls)

    def test_urls(self):
        """Test extraction of URLs."""
        test_cases = [
            # Basic URLs
            (
                "[https://example.com]",
                [],
                ["https://example.com"]
            ),
            # URLs with paths
            (
                "[https://example.com/path/to/resource]",
                [],
                ["https://example.com/path/to/resource"]
            ),
            # URLs with query parameters
            (
                "[https://example.com/search?q=test&lang=en]",
                [],
                ["https://example.com/search?q=test&lang=en"]
            ),
            # URLs without protocol
            (
                "[example.com/path]",
                [],
                ["example.com/path"]
            ),
            # URLs with subdomains
            (
                "[sub.example.com/path]",
                [],
                ["sub.example.com/path"]
            )
        ]

        for query, expected_files, expected_urls in test_cases:
            clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
            assert len(file_items) == len(expected_files)
            assert len(urls) == len(expected_urls)
            assert all(url == expected for url, expected in zip(urls, expected_urls))

    def test_edge_cases(self):
        """Test edge cases and potential ambiguous situations."""
        test_cases = [
            # File path that looks like a URL but starts with ./
            (
                "[./domain.com/file.txt]",
                ["./domain.com/file.txt"],
                []
            ),
            # File path that looks like a URL but starts with ../
            (
                "[../api.com/endpoint.json]",
                ["../api.com/endpoint.json"],
                []
            ),
            # File with multiple dots
            (
                "[file.test.js]",
                ["file.test.js"],
                []
            ),
            # Path with URL-like structure but should be a file
            (
                "[src/api.endpoint.js]",
                ["src/api.endpoint.js"],
                []
            ),
            # URL with dashes in domain
            (
                "[my-example.com/path]",
                [],
                ["my-example.com/path"]
            ),
            # Empty brackets
            (
                "[]",
                [],
                []
            ),
            # Multiple empty brackets
            (
                "[] [] []",
                [],
                []
            ),
            # Unclosed bracket
            (
                "[unclosed.txt",
                [],
                []
            ),
            # Nested brackets (current implementation treats them literally)
            (
                "[outer[inner]]",
                ["outer[inner]"],
                []
            )
        ]

        for query, expected_files, expected_urls in test_cases:
            clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
            assert len(file_items) == len(expected_files), f"Length mismatch for query '{query}': got {len(file_items)} items, expected {len(expected_files)}"
            
            # Print detailed information about what we got vs what we expected
            for i, (item, expected) in enumerate(zip(file_items, expected_files)):
                print(f"\nTesting query: {query}")
                print(f"Expected file path: {expected}")
                print(f"Got file item: {item}")
                assert item[0] == expected, f"Mismatch for query '{query}': got '{item[0]}', expected '{expected}'"
            
            assert len(urls) == len(expected_urls), f"URL length mismatch for query '{query}': got {len(urls)} urls, expected {len(expected_urls)}"
            assert all(url == expected for url, expected in zip(urls, expected_urls)), f"URL mismatch for query '{query}': got {urls}, expected {expected_urls}"

    def test_mixed_content(self):
        """Test queries containing both file paths and URLs."""
        test_cases = [
            # Mix of file and URL
            (
                "Compare [file.txt] with [example.com/api]",
                ["file.txt"],
                ["example.com/api"]
            ),
            # Complex mix with line ranges
            (
                "Check [file1.py:1-10], [https://docs.com], and [./src/test.js]",
                [("file1.py", 1, 10), "./src/test.js"],
                ["https://docs.com"]
            ),
            # URL-like file path and actual URL
            (
                "[./api.com/local.txt] vs [api.com/remote]",
                ["./api.com/local.txt"],
                ["api.com/remote"]
            )
        ]

        for query, expected_files, expected_urls in test_cases:
            clean_query, file_items, urls = code_assistant.extract_file_paths_and_urls(query)
            assert len(file_items) == len(expected_files)
            assert len(urls) == len(expected_urls)
            
            # Check file paths, handling both tuples and strings
            for item, expected in zip(file_items, expected_files):
                if isinstance(expected, tuple):
                    assert item == expected
                else:
                    assert item[0] == expected
            
            assert all(url == expected for url, expected in zip(urls, expected_urls)) 