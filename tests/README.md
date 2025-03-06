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

## Adding New Tests

To add new test cases:
1. Create a new test file in the `tests/` directory
2. Follow the pytest pattern for test functions
3. Update the benchmark.py file if needed to include new benchmark categories

For benchmark tests, add new entries to the respective test case lists in the Benchmarker class methods. 