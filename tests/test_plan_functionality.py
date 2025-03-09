"""
Tests for the project planning functionality of the code assistant.
"""
import os
import sys
import json
import pytest
import tempfile
from unittest.mock import patch, MagicMock, call
from io import StringIO

# Add the parent directory to the path so we can import code_assistant
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import code_assistant

# Sample JSON plan for testing
SAMPLE_PLAN_JSON = """[
    {
        "type": "create_file",
        "file_path": "hello.py"
    },
    {
        "type": "write_code",
        "file_path": "hello.py",
        "code": "print('Hello, World!')"
    },
    {
        "type": "run_command",
        "command": "python hello.py"
    },
    {
        "type": "run_command_and_check",
        "command": "python hello.py",
        "expected_output": "Hello, World!"
    }
]"""

# Sample LLM response containing JSON
SAMPLE_LLM_RESPONSE = f"""I've analyzed your request and broken it down into steps:

```json
{SAMPLE_PLAN_JSON}
```

These steps will create a simple Python script that prints 'Hello, World!' and run it to verify the output.
"""

@pytest.fixture
def mock_plan_response():
    """Returns a mock plan response from the LLM."""
    return SAMPLE_LLM_RESPONSE

@pytest.fixture
def mock_subprocess_run():
    """Mocks the subprocess.run function for testing command execution."""
    with patch('subprocess.run') as mock_run:
        # Configure the mock to return success for commands
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Hello, World!"
        mock_run.return_value = mock_result
        yield mock_run

@pytest.fixture
def mock_inputs():
    """Mocks the input function for testing user interaction."""
    with patch('builtins.input') as mock_input:
        # Set default responses for common prompts
        mock_input.side_effect = ['n', 'y', 'y', 'y', 'y']  # Standard sequence of inputs
        yield mock_input

@pytest.fixture
def mock_direct_api_request():
    """Mocks direct requests.post calls to the Ollama API."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": SAMPLE_PLAN_JSON
            }
        }
        mock_post.return_value = mock_response
        yield mock_post

def test_is_plan_query():
    """Test the is_plan_query function."""
    # Positive test cases
    assert code_assistant.is_plan_query("plan: Create a simple web server")
    assert code_assistant.is_plan_query("PLAN: Build a todo app")
    assert code_assistant.is_plan_query("vibeCheck: Let's create a neural network")
    assert code_assistant.is_plan_query("Plan this project: Calculator app")
    
    # Negative test cases
    assert not code_assistant.is_plan_query("How do I create a plan?")
    assert not code_assistant.is_plan_query("Tell me about planning in software")
    assert not code_assistant.is_plan_query("I need to plan something")
    assert not code_assistant.is_plan_query("search: how to plan a project")

def test_extract_plan_query():
    """Test the extract_plan_query function."""
    assert code_assistant.extract_plan_query("plan: Create a simple web server") == "Create a simple web server"
    assert code_assistant.extract_plan_query("PLAN: Build a todo app") == "Build a todo app"
    assert code_assistant.extract_plan_query("vibeCheck: Let's create a neural network") == "Let's create a neural network"
    assert code_assistant.extract_plan_query("Plan this project: Calculator app") == "Calculator app"
    
    # Complex examples
    assert code_assistant.extract_plan_query("plan: Create a web server with [app.py] and [server.py]") == "Create a web server with [app.py] and [server.py]"
    assert code_assistant.extract_plan_query("PLAN: Implement OAuth2 in [auth.py]") == "Implement OAuth2 in [auth.py]"

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_json_extraction_from_llm_response(mock_post, mock_get_response, mock_plan_response):
    """Test the JSON extraction functionality from LLM responses."""
    # Setup mock to return a response with JSON embedded in markdown
    mock_get_response.return_value = mock_plan_response
    
    # Mock the direct API request response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": SAMPLE_PLAN_JSON
        }
    }
    mock_post.return_value = mock_response
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Execute plan query
        conversation_history = []
        code_assistant.handle_plan_query("plan: Create a hello world script", conversation_history)
        
        # Verify that the JSON was extracted and steps were identified
        assert len(conversation_history) >= 2  # At least prompt and response
        response_content = conversation_history[1]["content"]
        assert "Hello, World!" in response_content
        
        # Make sure we parsed and identified the steps correctly
        assert mock_post.called

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_handle_plan_query_code_blocks(mock_post, mock_get_response):
    """Test handling of code blocks in plan queries."""
    # Setup mock to return a response with JSON in a code block
    code_block_response = """Here's the plan:

```json
[
    {
        "type": "create_file",
        "file_path": "example.py"
    },
    {
        "type": "write_code",
        "file_path": "example.py",
        "code": "print('Example')"
    }
]
```

This will create a simple Python script."""
    
    mock_get_response.return_value = code_block_response
    
    # Mock the direct API request response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": """[
                {
                    "type": "create_file",
                    "file_path": "example.py"
                },
                {
                    "type": "write_code",
                    "file_path": "example.py",
                    "code": "print('Example')"
                }
            ]"""
        }
    }
    mock_post.return_value = mock_response
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Execute plan query
        conversation_history = []
        code_assistant.handle_plan_query("plan: Create an example script", conversation_history)
        
        # Verify that the JSON was extracted properly from the code block
        assert len(conversation_history) >= 2  # At least prompt and response
        assert mock_post.called

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_handle_plan_query_malformed_json(mock_post, mock_get_response):
    """Test handling of malformed JSON in plan responses."""
    # First response with malformed JSON
    malformed_response = """Here's the plan:

```json
[
    {
        "type": "create_file",
        "file_path": "example.py"
    },
    {
        type: "write_code",
        "file_path": "example.py",
        "code": "print('Example')"
    }
]
```

This will create a simple Python script."""
    
    # Second response with correct JSON (for the retry)
    corrected_response = """[
    {
        "type": "create_file",
        "file_path": "example.py" 
    },
    {
        "type": "write_code",
        "file_path": "example.py",
        "code": "print('Example')"
    }
]"""
    
    # Setup the mock to return the malformed response first, then the corrected one
    mock_get_response.side_effect = [malformed_response, corrected_response]
    
    # Mock the direct API request responses
    bad_response = MagicMock()
    bad_response.status_code = 200
    bad_response.json.return_value = {
        "message": {
            "content": malformed_response
        }
    }
    
    good_response = MagicMock()
    good_response.status_code = 200
    good_response.json.return_value = {
        "message": {
            "content": corrected_response
        }
    }
    
    mock_post.side_effect = [bad_response, good_response]
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Execute plan query
        conversation_history = []
        code_assistant.handle_plan_query("plan: Create an example script", conversation_history)
        
        # Verify that the retry mechanism was triggered
        assert mock_get_response.call_count == 2
        assert mock_post.call_count == 2

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_execute_plan_steps(mock_post, mock_get_response, mock_plan_response, mock_subprocess_run, mock_inputs, temp_directory):
    """Test execution of plan steps."""
    # Change to the temporary directory
    original_dir = os.getcwd()
    try:
        os.chdir(temp_directory)
        
        # Setup mock to return a plan with all step types
        mock_get_response.return_value = mock_plan_response
        
        # Mock the direct API request response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": SAMPLE_PLAN_JSON
            }
        }
        mock_post.return_value = mock_response
        
        # Replace the mock_inputs with a sequence that will execute the plan
        mock_inputs.side_effect = ['n', 'y', 'y', 'y', 'y', 'y']
        
        with patch('builtins.print'):
            # Execute plan query
            conversation_history = []
            code_assistant.handle_plan_query("plan: Create a hello world script", conversation_history)
            
            # Verify that the file was created
            assert os.path.exists("hello.py")
            
            # Verify that the command was executed
            assert mock_subprocess_run.called
            
            # Get the command that was executed
            run_args = mock_subprocess_run.call_args_list[-1][0][0]
            assert "python hello.py" in ' '.join(run_args)
            
        # Clean up the created file
        if os.path.exists("hello.py"):
            os.remove("hello.py")
    finally:
        os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_execute_specific_step_types(mock_post, mock_get_response, mock_subprocess_run, mock_inputs, temp_directory):
    """Test execution of specific step types."""
    # Change to the temporary directory
    original_dir = os.getcwd()
    try:
        os.chdir(temp_directory)
        
        # Setup mock to return a plan with specific step types
        specific_plan = """[
            {
                "type": "create_file",
                "file_path": "test_file.txt"
            },
            {
                "type": "write_code",
                "file_path": "test_file.txt",
                "code": "This is test content."
            },
            {
                "type": "edit_file",
                "file_path": "test_file.txt",
                "original_pattern": "test content",
                "new_content": "updated content"
            },
            {
                "type": "run_command",
                "command": "type test_file.txt"
            }
        ]"""
        
        mock_get_response.return_value = specific_plan
        
        # Mock the direct API request response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": specific_plan
            }
        }
        mock_post.return_value = mock_response
        
        # Replace the mock_inputs with a sequence that will execute all steps
        mock_inputs.side_effect = ['n', 'y', 'y', 'y', 'y', 'y']
        
        with patch('builtins.print'), patch('code_assistant.generate_colored_diff', return_value="Diff preview"):
            # Execute plan query
            conversation_history = []
            code_assistant.handle_plan_query("plan: Create and modify a test file", conversation_history)
            
            # Verify the create_file step
            assert os.path.exists("test_file.txt")
            
            # Verify the write_code step
            with open("test_file.txt", "r") as f:
                content = f.read()
                assert "updated content" in content
            
            # Verify the run_command step
            assert mock_subprocess_run.called
            
            # Get the command that was executed
            run_args = mock_subprocess_run.call_args_list[-1][0][0]
            assert "type test_file.txt" in ' '.join(run_args)
            
        # Clean up the created file
        if os.path.exists("test_file.txt"):
            os.remove("test_file.txt")
    finally:
        os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_user_skipping_steps(mock_post, mock_get_response, mock_plan_response, mock_subprocess_run, temp_directory):
    """Test that users can skip steps in the plan."""
    # Change to the temporary directory
    original_dir = os.getcwd()
    try:
        os.chdir(temp_directory)
        
        # Setup mock to return a standard plan
        mock_get_response.return_value = mock_plan_response
        
        # Mock the direct API request response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": SAMPLE_PLAN_JSON
            }
        }
        mock_post.return_value = mock_response
        
        # Setup a mock input sequence that skips the second step
        with patch('builtins.input') as mock_input:
            mock_input.side_effect = ['n', 'y', 'y', 'n', 'y']
            
            with patch('builtins.print'):
                # Execute plan query
                conversation_history = []
                code_assistant.handle_plan_query("plan: Create a hello world script", conversation_history)
                
                # Verify that the file was created (first step)
                assert os.path.exists("hello.py")
                
                # Verify the content is empty (skipped the write step)
                with open("hello.py", "r") as f:
                    content = f.read()
                    assert content == ""
                
                # Verify that we still got to a later step
                assert mock_subprocess_run.called
                
            # Clean up the created file
            if os.path.exists("hello.py"):
                os.remove("hello.py")
    finally:
        os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_command_execution_error(mock_post, mock_get_response, mock_subprocess_run, mock_inputs, temp_directory):
    """Test handling of command execution errors."""
    # Change to the temporary directory
    original_dir = os.getcwd()
    try:
        os.chdir(temp_directory)
        
        # Setup mock to return a plan with a command that will fail
        failing_plan = """[
            {
                "type": "run_command",
                "command": "nonexistent_command"
            }
        ]"""
        
        mock_get_response.return_value = failing_plan
        
        # Mock the direct API request response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "message": {
                "content": failing_plan
            }
        }
        mock_post.return_value = mock_response
        
        # Setup the subprocess mock to simulate a failure
        failing_result = MagicMock()
        failing_result.returncode = 1
        failing_result.stderr = "Command not found"
        mock_subprocess_run.return_value = failing_result
        
        with patch('builtins.print') as mock_print, patch('builtins.input', return_value='y'):
            # Execute plan query
            conversation_history = []
            code_assistant.handle_plan_query("plan: Run a nonexistent command", conversation_history)
            
            # Verify that an error message was printed
            error_prints = [call for call in mock_print.call_args_list if "Error" in str(call) and "nonexistent_command" in str(call)]
            assert len(error_prints) > 0
    finally:
        os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_json_retry_mechanism(mock_post, mock_get_response, mock_inputs):
    """Test the JSON retry mechanism for malformed responses."""
    # First response with completely invalid content
    invalid_response = """I'm going to help you plan this project.

First, we should think about what steps we need:
1. Create the main file
2. Write the code
3. Test the code

Let me know if you'd like more details.
"""
    
    # Second response with valid JSON (for the retry)
    valid_response = """[
    {
        "type": "create_file",
        "file_path": "retry_test.py"
    },
    {
        "type": "write_code",
        "file_path": "retry_test.py",
        "code": "print('Retry worked!')"
    }
]"""
    
    # Setup the mock to return the invalid response first, then the valid one
    mock_get_response.side_effect = [invalid_response, valid_response]
    
    # Mock the direct API request responses
    bad_response = MagicMock()
    bad_response.status_code = 200
    bad_response.json.return_value = {
        "message": {
            "content": invalid_response
        }
    }
    
    good_response = MagicMock()
    good_response.status_code = 200
    good_response.json.return_value = {
        "message": {
            "content": valid_response
        }
    }
    
    mock_post.side_effect = [bad_response, good_response]
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Execute plan query
        conversation_history = []
        code_assistant.handle_plan_query("plan: Test retry mechanism", conversation_history)
        
        # Verify that the retry mechanism was triggered
        assert mock_get_response.call_count == 2
        assert mock_post.call_count == 2
        
        # Verify the final response contains the JSON from the valid response
        final_response = conversation_history[-1]["content"]
        assert "retry_test.py" in final_response

@patch('code_assistant.get_ollama_response')
@patch('requests.post')
def test_thinking_blocks_and_malformed_json(mock_post, mock_get_response, mock_inputs):
    """Test handling of thinking blocks in responses with malformed JSON."""
    # Response with thinking blocks and malformed JSON
    thinking_response = """<think>
I need to create a plan for this project. Let's break it down into steps:
1. Create a file for the script
2. Add code to the file
3. Run the script
</think>

Here's the plan:

```json
[
    {
        "type": "create_file",
        "file_path": "thinking_test.py"
    },
    {
        type: "write_code",  # Missing quotes around the type
        "file_path": "thinking_test.py",
        "code": "print('Thinking blocks handled correctly')"
    }
]
```
"""
    
    # Corrected response for the retry
    corrected_response = """[
    {
        "type": "create_file",
        "file_path": "thinking_test.py"
    },
    {
        "type": "write_code",
        "file_path": "thinking_test.py",
        "code": "print('Thinking blocks handled correctly')"
    }
]"""
    
    # Setup the mock to return the thinking response first, then the corrected one
    mock_get_response.side_effect = [thinking_response, corrected_response]
    
    # Mock the direct API request responses
    bad_response = MagicMock()
    bad_response.status_code = 200
    bad_response.json.return_value = {
        "message": {
            "content": thinking_response
        }
    }
    
    good_response = MagicMock()
    good_response.status_code = 200
    good_response.json.return_value = {
        "message": {
            "content": corrected_response
        }
    }
    
    mock_post.side_effect = [bad_response, good_response]
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Execute plan query
        conversation_history = []
        code_assistant.handle_plan_query("plan: Test thinking blocks", conversation_history)
        
        # Verify that the retry mechanism was triggered
        assert mock_get_response.call_count == 2
        assert mock_post.call_count == 2
        
        # Verify the final response contains the JSON from the corrected response
        final_response = conversation_history[-1]["content"]
        assert "thinking_test.py" in final_response

@patch('code_assistant.handle_plan_query')
def test_vibecode_alias_in_main_flow(mock_handle_plan):
    """Test that vibeCheck alias correctly routes to handle_plan_query."""
    # Setup a simple command line input
    sys.argv = ["code_assistant.py", "vibeCheck: Build a calculator"]
    
    # Define a mock implementation to capture the arguments
    captured_args = []
    def simulate_handle_plan(query, history, model=None, timeout=None):
        captured_args.append((query, history, model, timeout))
        return None
        
    mock_handle_plan.side_effect = simulate_handle_plan
    
    # Define a mock for the main command handling to bypass the rest of the function
    def simulate_command_flow(query):
        # Extract the type of query
        if code_assistant.is_plan_query(query):
            print("Handling plan query")
            code_assistant.handle_plan_query(query, [], None, None)
            return True
        return False
    
    # Execute the function with our mock
    with patch('code_assistant.handle_search_query'), patch('code_assistant.handle_edit_query'), \
         patch('code_assistant.handle_run_query'), patch('code_assistant.handle_model_query'), \
         patch('code_assistant.handle_create_query'), patch('code_assistant.handle_regular_query'), \
         patch('builtins.print'):
        # Call the main function
        try:
            # Patch only the internal function call
            with patch.object(code_assistant, 'handle_plan_query', side_effect=simulate_handle_plan):
                result = code_assistant.main()
        except SystemExit:
            pass  # Expected to exit after processing
        
    # Verify that handle_plan_query was called with the right arguments
    assert len(captured_args) == 1
    query, _, _, _ = captured_args[0]
    assert query == "vibeCheck: Build a calculator" 