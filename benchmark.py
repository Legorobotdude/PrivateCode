#!/usr/bin/env python3
"""
Benchmark tool for evaluating the local LLM coding assistant.

This script runs a series of benchmark tests to evaluate the assistant's performance
on different types of coding tasks and provides statistics on accuracy, response time,
and success rates.
"""

import os
import time
import json
import argparse
import tempfile
import shutil
import pytest
from unittest.mock import patch, MagicMock
import code_assistant
from tests.utils import create_test_file, create_mock_ollama_response

class BenchmarkResult:
    """Class to store and report benchmark results."""
    
    def __init__(self):
        self.results = []
    
    def add_result(self, task_type, task_name, success, time_taken, notes=""):
        """Add a benchmark result."""
        self.results.append({
            "task_type": task_type,
            "task_name": task_name,
            "success": success,
            "time_taken": time_taken,
            "notes": notes
        })
    
    def save_to_file(self, filename):
        """Save results to a JSON file."""
        with open(filename, 'w') as f:
            json.dump({"results": self.results}, f, indent=2)
    
    def load_from_file(self, filename):
        """Load results from a JSON file."""
        with open(filename, 'r') as f:
            data = json.load(f)
            self.results = data.get("results", [])
    
    def print_summary(self):
        """Print a summary of the benchmark results."""
        if not self.results:
            print("No benchmark results to display.")
            return
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r["success"])
        success_rate = (successful / total) * 100 if total > 0 else 0
        
        avg_time = sum(r["time_taken"] for r in self.results) / total if total > 0 else 0
        
        print(f"\n{'=' * 50}")
        print(f"BENCHMARK SUMMARY")
        print(f"{'=' * 50}")
        print(f"Total tasks: {total}")
        print(f"Successful tasks: {successful}")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Average time per task: {avg_time:.2f} seconds")
        print(f"{'=' * 50}")
        
        # Group by task type
        task_types = {}
        for r in self.results:
            task_type = r["task_type"]
            if task_type not in task_types:
                task_types[task_type] = {"total": 0, "success": 0, "time": 0}
            
            task_types[task_type]["total"] += 1
            if r["success"]:
                task_types[task_type]["success"] += 1
            task_types[task_type]["time"] += r["time_taken"]
        
        print("\nResults by task type:")
        print(f"{'Task Type':<20} {'Success Rate':<15} {'Avg Time (s)':<15}")
        print(f"{'-' * 50}")
        
        for task_type, stats in task_types.items():
            success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            avg_time = stats["time"] / stats["total"] if stats["total"] > 0 else 0
            print(f"{task_type:<20} {success_rate:>6.2f}%{'':<8} {avg_time:>6.2f}{'':<8}")


class Benchmarker:
    """Class to run benchmark tests on the coding assistant."""
    
    def __init__(self, model="codellama"):
        self.model = model
        self.results = BenchmarkResult()
        self.temp_dir = tempfile.mkdtemp()
    
    def cleanup(self):
        """Clean up temporary resources."""
        shutil.rmtree(self.temp_dir)
    
    def run_benchmarks(self):
        """Run all benchmark tests."""
        try:
            self._run_file_editing_tests()
            self._run_code_analysis_tests()
            self._run_command_detection_tests()
            self._run_query_classification_tests()
            
            self.results.print_summary()
            return self.results
        finally:
            self.cleanup()
    
    def _time_execution(self, task_type, task_name, func, *args, **kwargs):
        """Time the execution of a function and record the result."""
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            notes = ""
        except Exception as e:
            result = None
            success = False
            notes = str(e)
        
        time_taken = time.time() - start_time
        self.results.add_result(task_type, task_name, success, time_taken, notes)
        return result, success
    
    def _run_file_editing_tests(self):
        """Run tests for file editing functionality."""
        test_cases = [
            {
                "name": "Extract code block with language",
                "response": """Here's the updated file:
```python
def hello():
    print("Hello, world!")
```
It's a simple hello world function.""",
                "file_path": "test.py",
                "expected": 'def hello():\n    print("Hello, world!")'
            },
            {
                "name": "Extract code block without language",
                "response": """The fixed file is:
```
function add(a, b) {
    return a + b;
}
```
This corrects the previous bug.""",
                "file_path": "add.js",
                "expected": 'function add(a, b) {\n    return a + b;\n}'
            },
            {
                "name": "Extract multiple code blocks",
                "response": """First, let's create a small function:
```python
def small():
    pass
```

But actually, let's use this version:
```python
def better_function():
    return "Better result"
```""",
                "file_path": "functions.py",
                "expected": 'def better_function():\n    return "Better result"'
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            def _test():
                result = code_assistant.extract_modified_content(
                    test_case["response"], 
                    test_case["file_path"]
                )
                assert result == test_case["expected"]
                return result
            
            self._time_execution(
                "file_editing", 
                test_case["name"],
                _test
            )
    
    def _run_code_analysis_tests(self):
        """Run tests for code analysis functionality."""
        # Create test files
        python_file = create_test_file(
            self.temp_dir, 
            "buggy.py", 
            "def divide(a, b):\n    return a / b\n\nresult = divide(10, 0)"
        )
        
        js_file = create_test_file(
            self.temp_dir,
            "missing.js",
            "function getData() {\n    const data = fetchData();\n    return data;\n}\n\n// fetchData is not defined"
        )
        
        with patch('requests.post') as mock_post:
            # Test analyzing Python file with zero division error
            mock_post.return_value = create_mock_ollama_response(
                "The bug is a division by zero error in line 4. You should add a check to prevent dividing by zero."
            )
            
            def _test_python():
                history = [{"role": "user", "content": f"What's wrong with this code?\n\n{code_assistant.read_file_content(python_file)}"}]
                response = code_assistant.get_ollama_response(history, model=self.model)
                assert "division by zero" in response.lower()
                return response
            
            self._time_execution("code_analysis", "Identify division by zero", _test_python)
            
            # Test analyzing JavaScript with missing function
            mock_post.return_value = create_mock_ollama_response(
                "The code is trying to call 'fetchData()' but this function is not defined anywhere in the file."
            )
            
            def _test_js():
                history = [{"role": "user", "content": f"What's wrong with this code?\n\n{code_assistant.read_file_content(js_file)}"}]
                response = code_assistant.get_ollama_response(history, model=self.model)
                assert "not defined" in response.lower()
                return response
            
            self._time_execution("code_analysis", "Identify undefined function", _test_js)
    
    def _run_command_detection_tests(self):
        """Run tests for command detection functionality."""
        test_cases = [
            {
                "name": "Extract command from code block",
                "response": """You can run the tests with this command:
```
python -m pytest
```
This will execute all the tests in the project.""",
                "expected": "python -m pytest"
            },
            {
                "name": "Extract command with arguments",
                "response": """To list files with details, use:
```
ls -la
```""",
                "expected": "ls -la"
            },
            {
                "name": "Extract command with quoted arguments",
                "response": """Search for the pattern with:
```
grep "search pattern" *.py
```""",
                "expected": 'grep "search pattern" *.py'
            }
        ]
        
        for test_case in test_cases:
            def _test():
                result = code_assistant.extract_suggested_command(test_case["response"])
                assert result == test_case["expected"]
                return result
            
            self._time_execution(
                "command_detection", 
                test_case["name"],
                _test
            )
    
    def _run_query_classification_tests(self):
        """Run tests for query classification functionality."""
        test_cases = [
            {
                "name": "Classify search query",
                "func": code_assistant.is_search_query,
                "input": "search: python async examples",
                "expected": True
            },
            {
                "name": "Classify edit query",
                "func": code_assistant.is_edit_query,
                "input": "edit: app.py to fix error handling",
                "expected": True
            },
            {
                "name": "Classify run query",
                "func": code_assistant.is_run_query,
                "input": "run: python test.py",
                "expected": True
            },
            {
                "name": "Extract search query",
                "func": code_assistant.extract_search_query,
                "input": "search: best practices for error handling",
                "expected": "best practices for error handling"
            },
            {
                "name": "Extract edit query",
                "func": code_assistant.extract_edit_query,
                "input": "edit: main.py to improve performance",
                "expected": "main.py to improve performance"
            },
            {
                "name": "Extract run query",
                "func": code_assistant.extract_run_query,
                "input": "run: npm test -- --watch",
                "expected": "npm test -- --watch"
            }
        ]
        
        for test_case in test_cases:
            def _test():
                result = test_case["func"](test_case["input"])
                assert result == test_case["expected"]
                return result
            
            self._time_execution(
                "query_classification", 
                test_case["name"],
                _test
            )


def run_pytest_tests():
    """Run the pytest test suite and return the success status."""
    print("\nRunning pytest test suite...")
    result = pytest.main(["-xvs", "tests/"])
    return result == 0


def main():
    """Main function to run benchmarks."""
    parser = argparse.ArgumentParser(description="Benchmark the local LLM coding assistant")
    parser.add_argument("--model", default="codellama", help="The Ollama model to use")
    parser.add_argument("--output", default="benchmark_results.json", help="Output file for results")
    parser.add_argument("--run-tests", action="store_true", help="Run pytest tests before benchmarking")
    args = parser.parse_args()
    
    if args.run_tests:
        if not run_pytest_tests():
            print("Test suite failed. Aborting benchmarks.")
            return 1
    
    print(f"\nRunning benchmarks with model: {args.model}")
    benchmarker = Benchmarker(model=args.model)
    results = benchmarker.run_benchmarks()
    
    results.save_to_file(args.output)
    print(f"Benchmark results saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main()) 