# Examples for the Local LLM Coding Assistant

This directory contains example files for demonstrating and testing different features of the Local LLM Coding Assistant.

## Files

- **simple_hello.py**: A minimal example for basic code execution.
- **web_search_demo.py**: Demonstrates the web search capabilities with JSON parsing and API requests.
- **file_editing_demo.py**: Contains code that can be improved, demonstrating the file editing capabilities.
- **code_review_demo.py**: Example file with functions for code review demonstrations.
- **sample_text.txt**: A sample text file for file reading/writing operations.

## Usage

These files are intended to be used as examples when interacting with the coding assistant. For example:

```
How can I improve this code? [examples/file_editing_demo.py]
```

```
Help me understand this code. [examples/code_review_demo.py]
```

```
How can I implement the make_api_request function? [examples/web_search_demo.py]
```

## Running Tests

These are not part of the test suite. The actual tests are located in the `tests/` directory and can be run with pytest:

```
python -m pytest tests/
``` 