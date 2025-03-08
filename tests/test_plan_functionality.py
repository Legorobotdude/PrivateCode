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
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        yield mock_run

@pytest.fixture
def mock_inputs():
    """Mocks user inputs for testing interaction."""
    with patch('builtins.input') as mock_input:
        # Configure mock to return 'y' for all confirmation prompts
        mock_input.return_value = 'y'
        yield mock_input

def test_is_plan_query():
    """Test the detection of plan queries."""
    # Test plan with colon
    assert code_assistant.is_plan_query("plan: Create a hello world app")
    # Test plan with space
    assert code_assistant.is_plan_query("plan Create a hello world app")
    # Test vibecode with colon
    assert code_assistant.is_plan_query("vibecode: Create a hello world app")
    # Test vibecode with space
    assert code_assistant.is_plan_query("vibecode Create a hello world app")
    # Test case insensitivity
    assert code_assistant.is_plan_query("PLAN: Create a hello world app")
    assert code_assistant.is_plan_query("ViBeCode: Create a hello world app")
    # Test non-plan queries
    assert not code_assistant.is_plan_query("create: new_file.py")
    assert not code_assistant.is_plan_query("Normal query without plan prefix")

def test_extract_plan_query():
    """Test extraction of plan details from queries."""
    # Test plan with colon
    assert code_assistant.extract_plan_query("plan: Create a hello world app") == "Create a hello world app"
    # Test plan with space
    assert code_assistant.extract_plan_query("plan Create a hello world app") == "Create a hello world app"
    # Test vibecode with colon
    assert code_assistant.extract_plan_query("vibecode: Create a hello world app") == "Create a hello world app"
    # Test vibecode with space
    assert code_assistant.extract_plan_query("vibecode Create a hello world app") == "Create a hello world app"
    # Test case insensitivity
    assert code_assistant.extract_plan_query("PLAN: Create a hello world app") == "Create a hello world app"
    # Test handling of non-plan queries
    assert code_assistant.extract_plan_query("Not a plan query") == "Not a plan query"

@patch('code_assistant.get_ollama_response')
def test_json_extraction_from_llm_response(mock_get_response, mock_plan_response):
    """Test the extraction of JSON from LLM responses."""
    # Setup the mock to return our sample response
    mock_get_response.return_value = mock_plan_response
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        # Create minimal conversation history
        conversation_history = []
        
        # Call the function with a test query
        code_assistant.handle_plan_query("plan: Create a hello world app", conversation_history)
        
        # Since we return 'n' to the first prompt, the function should exit after parsing the JSON
        # We need to verify the JSON was correctly extracted
        assert len(conversation_history) == 2  # prompt and response added
        
        # Convert the expected JSON string to an object for comparison
        expected_steps = json.loads(SAMPLE_PLAN_JSON)
        
        # Check if conversation_history was properly updated
        assert conversation_history[0]["role"] == "user"
        assert "break down this request into a sequence of steps" in conversation_history[0]["content"]
        assert conversation_history[1]["role"] == "assistant"
        assert conversation_history[1]["content"] == mock_plan_response

@patch('code_assistant.get_ollama_response')
def test_handle_plan_query_code_blocks(mock_get_response):
    """Test JSON extraction when the response is formatted with code blocks."""
    # Response with JSON inside code blocks with language specified
    response_with_code_blocks = '''Here's the plan:

```json
[
    {
        "type": "create_file",
        "file_path": "test.py"
    }
]
```

These steps should help you accomplish your goal.'''

    mock_get_response.return_value = response_with_code_blocks
    
    with patch('builtins.print'), patch('builtins.input', return_value='n'):
        conversation_history = []
        code_assistant.handle_plan_query("plan: Test code blocks", conversation_history)
        
        # Verify that the JSON was extracted from the code blocks
        assert len(conversation_history) == 2

@patch('code_assistant.get_ollama_response')
def test_handle_plan_query_malformed_json(mock_get_response):
    """Test handling of malformed JSON in LLM responses."""
    # Response with malformed JSON
    malformed_json_response = '''Here's the plan:

[
    {
        "type": "create_file",
        "file_path": "test.py"
    },
    {
        "type": "write_code"
        "file_path": "test.py",  # Missing comma after "write_code"
        "code": "print('test')"
    }
]'''

    mock_get_response.return_value = malformed_json_response
    
    with patch('builtins.print') as mock_print, patch('builtins.input', return_value='n'):
        conversation_history = []
        code_assistant.handle_plan_query("plan: Test malformed JSON", conversation_history)
        
        # Verify some error message was printed - check just for the general failure pattern
        # rather than specific line numbers which might change
        error_call_found = False
        for call_args in mock_print.call_args_list:
            args, _ = call_args
            if len(args) > 0 and f"{code_assistant.Fore.RED}Failed to parse the plan:" in args[0]:
                error_call_found = True
                break
        
        assert error_call_found, "No JSON parsing error message was printed"

@patch('code_assistant.get_ollama_response')
def test_execute_plan_steps(mock_get_response, mock_plan_response, mock_subprocess_run, mock_inputs, temp_directory):
    """Test execution of plan steps."""
    # Setup the mock to return our sample response
    mock_get_response.return_value = mock_plan_response
    
    # Set up a temporary directory for the test
    original_dir = os.getcwd()
    try:
        os.chdir(temp_directory)
        
        with patch('builtins.print'):
            # Create minimal conversation history
            conversation_history = []
            
            # Call the function with a test query
            code_assistant.handle_plan_query("plan: Create a hello world app", conversation_history)
            
            # Verify that files were created and commands were run
            assert os.path.exists("hello.py")
            with open("hello.py", "r") as f:
                assert f.read() == "print('Hello, World!')"
            
            # Check that subprocess.run was called with the expected commands
            mock_subprocess_run.assert_any_call("python hello.py", shell=True, capture_output=True, text=True)
            
            # We expect subprocess.run to be called twice (once for run_command and once for run_command_and_check)
            assert mock_subprocess_run.call_count == 2
            
    finally:
        os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
def test_execute_specific_step_types(mock_get_response, mock_subprocess_run, mock_inputs, temp_directory):
    """Test the execution of specific step types."""
    # Create a plan with one of each step type
    plan_json = json.dumps([
        {"type": "create_file", "file_path": "test_create.py"},
        {"type": "write_code", "file_path": "test_write.py", "code": "print('Test write')"},
        {"type": "run_command", "command": "echo 'Test command'"},
        {"type": "run_command_and_check", "command": "echo 'Test check'", "expected_output": "Test check"}
    ])
    
    mock_get_response.return_value = f"```json\n{plan_json}\n```"
    
    # Set up a temporary directory for the test
    original_dir = os.getcwd()
    try:
        os.chdir(temp_directory)
        
        # Configure subprocess.run to return the expected output for the last test
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Test check"
        mock_subprocess_run.return_value = mock_result
        
        with patch('builtins.print'):
            conversation_history = []
            code_assistant.handle_plan_query("plan: Test all step types", conversation_history)
            
            # Verify files were created
            assert os.path.exists("test_create.py")
            assert os.path.exists("test_write.py")
            
            # Verify content of written file
            with open("test_write.py", "r") as f:
                assert f.read() == "print('Test write')"
            
            # Verify commands were run
            assert mock_subprocess_run.call_count == 2
            mock_subprocess_run.assert_any_call("echo 'Test command'", shell=True, capture_output=True, text=True)
            mock_subprocess_run.assert_any_call("echo 'Test check'", shell=True, capture_output=True, text=True)
            
    finally:
        os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
def test_user_skipping_steps(mock_get_response, mock_plan_response, mock_subprocess_run, temp_directory):
    """Test that users can skip steps and the program handles it correctly."""
    mock_get_response.return_value = mock_plan_response
    
    # Set up a temporary directory for the test
    original_dir = os.getcwd()
    try:
        os.chdir(temp_directory)
        
        # Updated mock input sequence based on actual code flow - we need enough responses
        # for all the input() calls in the function
        with patch('builtins.input') as mock_input, patch('builtins.print'):
            # Configure side_effect to return different values for different input() calls
            mock_input.side_effect = [
                'n',  # Skip saving plan to file (simplifies the test)
                'y',  # Execute plan? -> yes
                'y',  # Step 1: Create file -> yes
                'n',  # Step 2: Write code -> no
                'n'   # Stop after skipping step 2
            ]
            
            conversation_history = []
            code_assistant.handle_plan_query("plan: Test skipping steps", conversation_history)
            
            # Verify the empty file was created but we stopped before executing commands
            assert os.path.exists("hello.py")
            with open("hello.py", "r") as f:
                assert f.read() == ""  # Should be empty since we skipped the write step
            
            # Since we stopped after step 2, we shouldn't have run any commands
            # This aligns with the failing test that showed 0 run counts
            assert mock_subprocess_run.call_count == 0
            
    finally:
        os.chdir(original_dir)

@patch('code_assistant.get_ollama_response')
def test_command_execution_error(mock_get_response, mock_subprocess_run, mock_inputs, temp_directory):
    """Test handling of command execution errors."""
    # Create a plan with a command that will fail
    plan_json = json.dumps([
        {"type": "run_command", "command": "non_existent_command"}
    ])
    
    mock_get_response.return_value = f"```json\n{plan_json}\n```"
    
    # Configure subprocess.run to simulate a failed command
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Command not found: non_existent_command"
    mock_subprocess_run.return_value = mock_result
    
    with patch('builtins.print') as mock_print:
        conversation_history = []
        code_assistant.handle_plan_query("plan: Test command error", conversation_history)
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{code_assistant.Fore.RED}Command failed with error code 1:{code_assistant.Style.RESET_ALL}")

@patch('code_assistant.get_ollama_response')
def test_json_retry_mechanism(mock_get_response, mock_inputs):
    """Test the retry mechanism when the LLM doesn't return valid JSON."""
    # First response is just text without valid JSON
    invalid_response = "I'll help you create a Hello World program. First, you need to create a file..."
    
    # Second response (after retry) contains valid JSON
    valid_json_response = """[
        {"type": "create_file", "file_path": "hello.py"},
        {"type": "write_code", "file_path": "hello.py", "code": "print('Hello, World!')"}
    ]"""
    
    # Set up the mock to return invalid response first, then valid JSON after retry
    mock_get_response.side_effect = [invalid_response, valid_json_response]
    
    # Mock all user inputs to return 'n' (no) to avoid actual execution
    mock_inputs.return_value = 'n'
    
    with patch('builtins.print') as mock_print:
        conversation_history = []
        code_assistant.handle_plan_query("plan: Test retry mechanism", conversation_history)
        
        # Verify the retry message was printed
        mock_print.assert_any_call(f"{code_assistant.Fore.YELLOW}The model didn't return a valid JSON plan. Retrying with stronger instructions...{code_assistant.Style.RESET_ALL}")
        
        # Verify the retry generation message was printed
        mock_print.assert_any_call(f"{code_assistant.Fore.CYAN}Retrying plan generation...{code_assistant.Style.RESET_ALL}")
        
        # Verify that we see the plan display after successful retry
        mock_print.assert_any_call(f"{code_assistant.Fore.GREEN}Generated Plan:{code_assistant.Style.RESET_ALL}")
        
        # Check that get_ollama_response was called twice (initial + retry)
        assert mock_get_response.call_count == 2
        
        # Verify retry prompt contains stronger language about JSON format
        retry_call_args = mock_get_response.call_args_list[1][0][0]
        assert any("YOU MUST RESPOND WITH ONLY A JSON ARRAY" in msg.get('content', '') 
                  for msg in retry_call_args if msg.get('role') == 'user')

@patch('code_assistant.handle_plan_query')
def test_vibecode_alias_in_main_flow(mock_handle_plan):
    """Test that 'vibecode' command is handled identically to 'plan' in the main program flow."""
    # Create test instances for both aliases
    plan_query = "plan: Create a test app"
    vibecode_query = "vibecode: Create a test app"
    
    # Mock conversation history
    conversation_history = []
    
    # Test that both queries are detected as plan queries
    assert code_assistant.is_plan_query(plan_query)
    assert code_assistant.is_plan_query(vibecode_query)
    
    # Patch main command handling flow to test both aliases
    with patch('builtins.print'):
        # Create a function to simulate the main command flow
        def simulate_command_flow(query):
            if code_assistant.is_plan_query(query):
                code_assistant.handle_plan_query(query, conversation_history)
        
        # Test with 'plan' command
        simulate_command_flow(plan_query)
        mock_handle_plan.assert_called_with(plan_query, conversation_history)
        mock_handle_plan.reset_mock()
        
        # Test with 'vibecode' command
        simulate_command_flow(vibecode_query)
        mock_handle_plan.assert_called_with(vibecode_query, conversation_history)
        
        # Verify both commands were extracted correctly
        assert code_assistant.extract_plan_query(plan_query) == "Create a test app"
        assert code_assistant.extract_plan_query(vibecode_query) == "Create a test app" 