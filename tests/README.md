# Test Suite for Local LLM Coding Assistant

This directory contains a comprehensive test suite for the Local LLM Coding Assistant. The tests are designed to validate different components of the assistant and provide metrics for performance evaluation.

## Test Components

The test suite includes the following components:

1. **Unit Tests:** Tests for individual functions and components
   - File operations (read/write/detect encoding)
   - Content extraction (from LLM responses)
   - Command execution and safety checks
   - Web search functionality
   - Ollama API interaction
     - Connection verification
     - Response handling
     - Comprehensive error handling (timeouts, connection issues, HTTP errors, JSON parsing)
   - Planning functionality
     - File content inclusion
     - Step execution
     - Error handling

2. **Benchmarks:** Performance tests to evaluate the assistant's capabilities
   - Response time measurement
   - Accuracy evaluation
   - Success rate tracking

## Running the Tests

### Prerequisites

Ensure you have all the required dependencies installed:

```
pip install -r ../requirements.txt
```

### Running Unit Tests

To run all unit tests:

```
python -m pytest tests/
```

To run specific test modules:

```
python -m pytest tests/test_file_operations.py
python -m pytest tests/test_content_extraction.py
python -m pytest tests/test_command_execution.py
python -m pytest tests/test_web_search.py
python -m pytest tests/test_ollama_api.py
python -m pytest tests/test_plan_file_content.py
```

To run tests with verbose output:

```
python -m pytest -v tests/
```

To run tests with code coverage report:

```
python -m pytest --cov=code_assistant tests/
```

### Running Benchmarks

The benchmark tool can be run with:

```
python benchmark.py --model codellama
```

Additional options:
- `--output filename.json`: Specify output file for results (default: benchmark_results.json)
- `--charts directory_name`: Specify directory for benchmark charts (default: benchmark_charts)
- `--run-tests`: Run pytest tests before benchmarking

## Benchmark Results

Benchmark results will be saved as a JSON file and include:
- Success rates for different task types
- Average response times
- Detailed information for each test case

Visualization charts will be generated in the specified output directory, showing:
- Success rate by task type
- Average time by task type
- Success vs time correlation

## Error Handling Tests

We have extensive test coverage for error handling, particularly for the `get_ollama_response` function which includes tests for:

1. **Network Errors**
   - Timeouts (ensuring appropriate timeout messages)
   - Connection errors (verifying helpful error messages)

2. **HTTP Errors**
   - 404 Not Found (model not found)
   - 400 Bad Request
   - 500 Internal Server Error
   - Other status codes

3. **Data Processing Errors**
   - JSON decode errors
   - Empty response content
   - Malformed responses

These tests ensure users receive precise, actionable error messages that help troubleshoot problems with the Ollama API integration.

## Testing the Planning Functionality

The planning functionality tests in `test_plan_file_content.py` verify:

1. **File Content Inclusion**: Tests that file contents referenced in planning queries are correctly included in the prompt.
2. **Multiple File Handling**: Tests that multiple files can be referenced and included in a single plan.
3. **Edit File Steps**: Tests that edit operations are correctly parsed and can be executed.
4. **Nonexistent File Handling**: Tests that the planner gracefully handles references to files that don't exist.

### Important Notes for Testing Planning Functionality

When testing the planning functionality, be aware that:

1. **Direct API Calls**: The `handle_plan_query` function makes direct calls to the Ollama API using `requests.post()` rather than using the `get_ollama_response` function for some operations. Make sure to mock both:
   ```python
   @patch('code_assistant.get_ollama_response')
   @patch('requests.post')
   def test_planning_function(mock_requests_post, mock_get_response):
       # Setup mock responses
       mock_requests_post.return_value = MagicMock(status_code=200, ...)
   ```

2. **Multiple User Inputs**: Plan execution requires multiple user confirmations. Be sure to provide enough values for all prompts:
   ```python
   with patch('builtins.input', side_effect=['n', 'y', 'y', 'n']):
       # Execute test
   ```

## Adding New Tests

To add new test cases:
1. Create a new test file in the `tests/` directory
2. Follow the pytest pattern for test functions
3. Update the benchmark.py file if needed to include new benchmark categories

For benchmark tests, add new entries to the respective test case lists in the Benchmarker class methods. 