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
        total_tasks = len(self.results)
        successful_tasks = sum(1 for r in self.results if r["success"])
        success_rate = (successful_tasks / total_tasks) * 100 if total_tasks > 0 else 0
        avg_time = sum(r["time_taken"] for r in self.results) / total_tasks if total_tasks > 0 else 0
        
        print("\n==================================================")
        print("BENCHMARK SUMMARY")
        print("==================================================")
        print(f"Total tasks: {total_tasks}")
        print(f"Successful tasks: {successful_tasks}")
        print(f"Success rate: {success_rate:.2f}%")
        print(f"Average time per task: {avg_time:.2f} seconds")
        print("==================================================\n")
        
        # Group results by task type
        task_types = {}
        for result in self.results:
            task_type = result["task_type"]
            if task_type not in task_types:
                task_types[task_type] = {
                    "total": 0,
                    "success": 0,
                    "time": 0
                }
            
            task_types[task_type]["total"] += 1
            if result["success"]:
                task_types[task_type]["success"] += 1
            task_types[task_type]["time"] += result["time_taken"]
        
        # Print results by task type
        print("Results by task type:")
        print(f"{'Task Type':<20} {'Success Rate':<15} {'Avg Time (s)':<15}")
        print("-" * 50)
        
        for task_type, stats in sorted(task_types.items()):
            success_rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
            avg_time = stats["time"] / stats["total"] if stats["total"] > 0 else 0
            print(f"{task_type:<20} {success_rate:>6.2f}% {' '*8} {avg_time:>6.2f}")


class Benchmarker:
    """Class to run benchmark tests on the coding assistant."""
    
    def __init__(self, model="qwq", timeout=60):
        self.model = model
        self.results = BenchmarkResult()
        self.temp_dir = tempfile.mkdtemp()
        self.use_real_llm = True  # Use real LLM by default
        self.timeout = timeout  # Timeout for LLM operations in seconds
    
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
            self._run_partial_file_reading_tests()
            
            self.results.print_summary()
            return self.results
        finally:
            self.cleanup()
    
    def _time_execution(self, task_type, task_name, func, *args, **kwargs):
        """Time the execution of a function and record the result."""
        print(f"Running {task_type}: {task_name}...")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            notes = ""
            print(f"  ✓ Success")
        except Exception as e:
            result = None
            success = False
            notes = str(e)
            print(f"  ✗ Failed: {notes}")
        
        time_taken = time.time() - start_time
        self.results.add_result(task_type, task_name, success, time_taken, notes)
        return result
    
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
        
        if not self.use_real_llm:
            # Use mocked responses for testing extraction logic
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
        else:
            # Use real LLM calls for file editing tests
            # Create test files with simple bugs to fix
            python_file = create_test_file(
                self.temp_dir,
                "buggy_function.py",
                "def hello(name)\n    print('Hello, ' + name)"  # Missing colon after parameter
            )
            
            js_file = create_test_file(
                self.temp_dir,
                "buggy_js.js",
                "function add(a, b) {\n    return a + b"  # Missing closing brace and semicolon
            )
            
            # Create C# file with a simple bug
            csharp_file = create_test_file(
                self.temp_dir,
                "buggy_csharp.cs",
                "using System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine(\"Hello, World!\"\n    }\n}"  # Missing closing parenthesis
            )
            
            # Create C++ file with a simple bug
            cpp_file = create_test_file(
                self.temp_dir,
                "buggy_cpp.cpp",
                "#include <iostream>\n\nint main() {\n    std::cout << \"Hello, World!\";\n    return 0"  # Missing semicolon after return statement
            )
            
            # Create HTML file with a simple bug
            html_file = create_test_file(
                self.temp_dir,
                "buggy_html.html",
                "<!DOCTYPE html>\n<html>\n<head>\n    <title>Test Page</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n    <p>This is a test page.<p>\n</body>\n</html>"  # Missing closing </p> tag
            )
            
            # Test Python file fix
            def _test_python_fix():
                history = [
                    {"role": "user", "content": f"Fix this Python code by adding the missing colon after the parameter:\n\n{code_assistant.read_file_content(python_file)}"}
                ]
                response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
                modified = code_assistant.extract_modified_content(response, python_file)
                # Check if the colon was added
                assert "def hello(name):" in modified
                return modified
            
            self._time_execution("file_editing", "Fix Python syntax (real LLM)", _test_python_fix)
            
            # Test JavaScript file fix
            def _test_js_fix():
                try:
                    history = [
                        {"role": "user", "content": f"Fix this JavaScript code by adding the missing closing brace and semicolon:\n\n{code_assistant.read_file_content(js_file)}"}
                    ]
                    response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
                    
                    # If we got an error response due to timeout, try a simpler prompt
                    if "timeout" in response.lower():
                        print("Retrying with a simpler prompt...")
                        history = [
                            {"role": "user", "content": f"Add the missing closing brace and semicolon to this JavaScript code:\n\nfunction add(a, b) {{\n    return a + b"}
                        ]
                        response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
                    
                    modified = code_assistant.extract_modified_content(response, js_file)
                    
                    # If extraction failed, try a manual approach
                    if not modified and response:
                        print("Extraction failed, trying manual approach...")
                        # Look for code between backticks
                        if "```" in response:
                            code_blocks = response.split("```")
                            if len(code_blocks) > 1:
                                code = code_blocks[1].strip()
                                if code.startswith("javascript") or code.startswith("js"):
                                    code = "\n".join(code.split("\n")[1:])
                                modified = code
                    
                    # Check if the closing brace and semicolon were added
                    if modified:
                        assert "return a + b;" in modified and "}" in modified
                    else:
                        raise Exception("Failed to extract valid JavaScript code")
                    return modified
                except Exception as e:
                    print(f"Error in JavaScript test: {e}")
                    raise  # Re-raise the exception instead of returning False
            
            self._time_execution("file_editing", "Fix JavaScript syntax (real LLM)", _test_js_fix)
            
            # Test C# file fix
            def _test_csharp_fix():
                try:
                    history = [
                        {"role": "user", "content": f"Fix this C# code by adding the missing closing parenthesis:\n\n{code_assistant.read_file_content(csharp_file)}"}
                    ]
                    response = code_assistant.get_ollama_response(history, model=self.model)
                    
                    # If we got an error response due to timeout, try a simpler prompt
                    if "timeout" in response.lower():
                        print("Retrying with a simpler prompt...")
                        history = [
                            {"role": "user", "content": "Add the missing closing parenthesis to this C# code:\n\nusing System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine(\"Hello, World!\");\n    }\n}"}
                        ]
                        response = code_assistant.get_ollama_response(history, model=self.model)
                    
                    modified = code_assistant.extract_modified_content(response, csharp_file)
                    
                    # If extraction failed, try a manual approach
                    if not modified and response:
                        print("Extraction failed, trying manual approach...")
                        # Look for code between backticks
                        if "```" in response:
                            code_blocks = response.split("```")
                            if len(code_blocks) > 1:
                                code = code_blocks[1].strip()
                                if code.startswith("csharp") or code.startswith("cs"):
                                    code = "\n".join(code.split("\n")[1:])
                                modified = code
                    
                    # Check if the closing parenthesis was added
                    if modified:
                        assert "Console.WriteLine(\"Hello, World!\");" in modified
                    else:
                        raise Exception("Failed to extract valid C# code")
                    return modified
                except Exception as e:
                    print(f"Error in C# test: {e}")
                    raise  # Re-raise the exception instead of returning False
            
            self._time_execution("file_editing", "Fix C# syntax (real LLM)", _test_csharp_fix)
            
            # Test C++ file fix
            def _test_cpp_fix():
                try:
                    history = [
                        {"role": "user", "content": f"Fix this C++ code by adding the missing semicolon after the return statement:\n\n{code_assistant.read_file_content(cpp_file)}"}
                    ]
                    response = code_assistant.get_ollama_response(history, model=self.model)
                    
                    # If we got an error response due to timeout, try a simpler prompt
                    if "timeout" in response.lower():
                        print("Retrying with a simpler prompt...")
                        history = [
                            {"role": "user", "content": "Add the missing semicolon after the return statement in this C++ code:\n\n#include <iostream>\n\nint main() {\n    std::cout << \"Hello, World!\";\n    return 0\n}"}
                        ]
                        response = code_assistant.get_ollama_response(history, model=self.model)
                    
                    modified = code_assistant.extract_modified_content(response, cpp_file)
                    
                    # If extraction failed, try a manual approach
                    if not modified and response:
                        print("Extraction failed, trying manual approach...")
                        # Look for code between backticks
                        if "```" in response:
                            code_blocks = response.split("```")
                            if len(code_blocks) > 1:
                                code = code_blocks[1].strip()
                                if code.startswith("cpp") or code.startswith("c++"):
                                    code = "\n".join(code.split("\n")[1:])
                                modified = code
                    
                    # Check if the semicolon was added
                    if modified:
                        assert "return 0;" in modified
                    else:
                        raise Exception("Failed to extract valid C++ code")
                    return modified
                except Exception as e:
                    print(f"Error in C++ test: {e}")
                    raise  # Re-raise the exception instead of returning False
            
            self._time_execution("file_editing", "Fix C++ syntax (real LLM)", _test_cpp_fix)
            
            # Test HTML file fix
            def _test_html_fix():
                try:
                    history = [
                        {"role": "user", "content": f"Fix this HTML code by adding the missing closing </p> tag:\n\n{code_assistant.read_file_content(html_file)}"}
                    ]
                    response = code_assistant.get_ollama_response(history, model=self.model)
                    
                    # If we got an error response due to timeout, try a simpler prompt
                    if "timeout" in response.lower():
                        print("Retrying with a simpler prompt...")
                        history = [
                            {"role": "user", "content": "Add the missing closing </p> tag to this HTML code:\n\n<!DOCTYPE html>\n<html>\n<head>\n    <title>Test Page</title>\n</head>\n<body>\n    <h1>Hello, World!</h1>\n    <p>This is a test page.<p>\n</body>\n</html>"}
                        ]
                        response = code_assistant.get_ollama_response(history, model=self.model)
                    
                    modified = code_assistant.extract_modified_content(response, html_file)
                    
                    # If extraction failed, try a manual approach
                    if not modified and response:
                        print("Extraction failed, trying manual approach...")
                        # Look for code between backticks
                        if "```" in response:
                            code_blocks = response.split("```")
                            if len(code_blocks) > 1:
                                code = code_blocks[1].strip()
                                if code.startswith("html"):
                                    code = "\n".join(code.split("\n")[1:])
                                modified = code
                    
                    # Check if the closing tag was added
                    if modified:
                        assert "<p>This is a test page.</p>" in modified
                    else:
                        raise Exception("Failed to extract valid HTML code")
                    return modified
                except Exception as e:
                    print(f"Error in HTML test: {e}")
                    raise  # Re-raise the exception instead of returning False
            
            self._time_execution("file_editing", "Fix HTML syntax (real LLM)", _test_html_fix)
    
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
        
        if not self.use_real_llm:
            # Use mocked responses
            with patch('requests.post') as mock_post:
                # Test analyzing Python file with zero division error
                mock_post.return_value = create_mock_ollama_response(
                    "The bug is a division by zero error in line 4. You should add a check to prevent dividing by zero."
                )
                
                def _test_python():
                    history = [{"role": "user", "content": f"What's wrong with this code?\n\n{code_assistant.read_file_content(python_file)}"}]
                    response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
                    assert "division by zero" in response.lower()
                    return response
                
                self._time_execution("code_analysis", "Identify division by zero", _test_python)
                
                # Test analyzing JavaScript with missing function
                mock_post.return_value = create_mock_ollama_response(
                    "The code is trying to call 'fetchData()' but this function is not defined anywhere in the file."
                )
                
                def _test_js():
                    history = [{"role": "user", "content": f"What's wrong with this code?\n\n{code_assistant.read_file_content(js_file)}"}]
                    response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
                    assert "not defined" in response.lower()
                    return response
                
                self._time_execution("code_analysis", "Identify undefined function", _test_js)
        else:
            # Use real LLM calls
            def _test_python():
                history = [{"role": "user", "content": f"What's wrong with this code?\n\n{code_assistant.read_file_content(python_file)}"}]
                response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
                # More flexible assertion for real LLM responses
                assert any(phrase in response.lower() for phrase in ["division by zero", "divide by zero", "denominator is zero", "zero division"])
                return response
            
            self._time_execution("code_analysis", "Identify division by zero (real LLM)", _test_python)
            
            def _test_js():
                history = [{"role": "user", "content": f"What's wrong with this code?\n\n{code_assistant.read_file_content(js_file)}"}]
                response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
                # More flexible assertion for real LLM responses
                assert any(phrase in response.lower() for phrase in ["not defined", "undefined", "missing", "doesn't exist"])
                return response
            
            self._time_execution("code_analysis", "Identify undefined function (real LLM)", _test_js)
    
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

    def _run_partial_file_reading_tests(self):
        """Run tests for the partial file reading feature."""
        # Create a test file with multiple lines
        test_content = "\n".join([f"Line {i}: This is test content line {i}" for i in range(1, 101)])
        test_file = create_test_file(self.temp_dir, "large_file.txt", test_content)
        
        # Test reading specific line ranges
        def _test_read_line_range():
            # Test with a specific line range (lines 10-20)
            # Use brackets around the file path and line range separately to avoid issues with Windows paths
            query = f"Analyze lines 10-20 of [large_file.txt:10-20]"
            # Manually construct the file items to avoid issues with Windows paths
            file_items = [(test_file, 10, 20)]
            
            file_path, start_line, end_line = file_items[0]
            content = code_assistant.read_file_content(file_path, start_line, end_line)
            
            # Verify that only the requested lines are included
            assert "Line 10:" in content
            assert "Line 20:" in content
            assert "Line 9:" not in content
            assert "Line 21:" not in content
            
            # Verify the line info header is included
            assert "Lines 10-20" in content
            
            return True
        
        # Test reading from a specific line to the end
        def _test_read_from_line():
            # Manually construct the file items
            file_items = [(test_file, 90, None)]
            
            file_path, start_line, end_line = file_items[0]
            content = code_assistant.read_file_content(file_path, start_line, end_line)
            
            # Verify that only the requested lines are included
            assert "Line 90:" in content
            assert "Line 100:" in content
            assert "Line 89:" not in content
            
            return True
        
        # Test reading from the beginning to a specific line
        def _test_read_to_line():
            # Manually construct the file items
            file_items = [(test_file, None, 10)]
            
            file_path, start_line, end_line = file_items[0]
            content = code_assistant.read_file_content(file_path, start_line, end_line)
            
            # Verify that only the requested lines are included
            assert "Line 1:" in content
            assert "Line 10:" in content
            assert "Line 11:" not in content
            
            return True
        
        # Test reading a single line
        def _test_read_single_line():
            # Manually construct the file items
            file_items = [(test_file, 42, 42)]  # End is inclusive in read_file_content
            
            file_path, start_line, end_line = file_items[0]
            content = code_assistant.read_file_content(file_path, start_line, end_line)
            
            # Verify that only the requested line is included
            assert "Line 42:" in content
            assert "Line 41:" not in content
            assert "Line 43:" not in content
            
            return True
        
        # Test with real LLM to analyze partial file
        def _test_llm_partial_file_analysis():
            if not self.use_real_llm:
                return True  # Skip if not using real LLM
                
            # Create a file with a bug in a specific line range
            bug_content = "\n".join([
                "def calculate_sum(numbers):",
                "    total = 0",
                "    for num in numbers:",
                "        total += num",
                "    return total",
                "",
                "def calculate_average(numbers):",
                "    if len(numbers) == 0:",
                "        return 0",
                "    total = calculate_sum(numbers)",
                "    # Bug is here - should divide by len(numbers)",
                "    return total / 0",  # Division by zero bug
                "",
                "result = calculate_average([1, 2, 3, 4, 5])"
            ])
            
            bug_file = create_test_file(self.temp_dir, "bug_in_range.py", bug_content)
            
            # Manually construct the file items
            file_items = [(bug_file, 6, 12)]
            
            file_path, start_line, end_line = file_items[0]
            partial_content = code_assistant.read_file_content(file_path, start_line, end_line)
            
            history = [{"role": "user", "content": f"What's wrong with this function?\n\n{partial_content}"}]
            response = code_assistant.get_ollama_response(history, model=self.model, timeout=self.timeout)
            
            # Check if the response identifies the division by zero issue
            assert response is not None
            assert "division by zero" in response.lower() or "divide by zero" in response.lower() or "zero" in response.lower()
            
            return True
        
        # Run the tests
        self._time_execution("partial_file_reading", "Read specific line range", _test_read_line_range)
        self._time_execution("partial_file_reading", "Read from specific line to end", _test_read_from_line)
        self._time_execution("partial_file_reading", "Read from beginning to specific line", _test_read_to_line)
        self._time_execution("partial_file_reading", "Read single line", _test_read_single_line)
        self._time_execution("partial_file_reading", "LLM analysis of partial file", _test_llm_partial_file_analysis)


def run_pytest_tests():
    """Run the pytest test suite and return the success status."""
    print("\nRunning pytest test suite...")
    result = pytest.main(["-xvs", "tests/"])
    return result == 0


def main():
    """Main function to run benchmarks."""
    parser = argparse.ArgumentParser(description="Benchmark the local LLM coding assistant")
    parser.add_argument("--model", default="qwq", help="The Ollama model to use")
    parser.add_argument("--output", default="benchmark_results.json", help="Output file for results")
    parser.add_argument("--run-tests", action="store_true", help="Run pytest tests before benchmarking")
    parser.add_argument("--use-mocks", action="store_true", help="Use mock responses instead of real LLM calls")
    parser.add_argument("--timeout", type=int, default=60, help="Timeout in seconds for LLM operations (default: 60)")
    args = parser.parse_args()
    
    if args.run_tests:
        if not run_pytest_tests():
            print("Test suite failed. Aborting benchmarks.")
            return 1
    
    print(f"\nRunning benchmarks with model: {args.model}")
    benchmarker = Benchmarker(model=args.model, timeout=args.timeout)
    
    # Set use_real_llm based on the use-mocks flag (inverted logic)
    benchmarker.use_real_llm = not args.use_mocks
    if args.use_mocks:
        print("Using mock responses for benchmarks (faster but less realistic)")
    else:
        print(f"Using real LLM calls for benchmarks with a timeout of {args.timeout} seconds")
    
    # Run the benchmarks
    results = benchmarker.run_benchmarks()
    
    # Save results to file
    results.save_to_file(args.output)
    print(f"\nBenchmark results saved to {args.output}")
    
    return 0


if __name__ == "__main__":
    exit(main()) 