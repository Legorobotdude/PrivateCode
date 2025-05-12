# Vibecoder.gg (Local LLM Coding Assistant)

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

A terminal-based coding assistant that uses local Large Language Models (LLMs) via Ollama to provide coding help and answer programming questions. The assistant can also search the web for information while maintaining privacy, edit files, and execute commands with user confirmation.

## Features

- Interactive terminal interface
- Context-aware coding assistance
- File inclusion for code context
- Partial file reading with line range specification
- Web search capabilities with DuckDuckGo
- URL content extraction for reference
- Intelligent file editing with diff preview
- Safe command execution with LLM suggestions
- Create new files with a simple command
- Create and edit new files in one step
- Persistent conversation history
- Locally hosted LLM (no data sent to external services)
- AI thinking blocks with configurable display options
- Project planning with step-by-step execution (plan/vibecode feature)

## Prerequisites

- Python 3.6+
- [Ollama](https://ollama.ai/) installed and running locally
- A code LLM model pulled in Ollama (e.g., codellama, llama2, mixtral)
- (optional) Internet connection (for web search functionality)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/Legorobotdude/local-llm-coding-assistant.git
   cd local-llm-coding-assistant
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Make sure Ollama is running on your system:
   ```
   # On Windows, Ollama should be running in the background
   # You can check its status in the system tray
   ```

4. Pull a code-focused LLM if you haven't already:
   ```
   ollama pull codellama
   ```

## Usage

1. Run the coding assistant:
   ```
   python code_assistant.py
   ```

2. Enter your coding questions and include file paths in square brackets.
   
   Example:
   ```
   > What does this function do? [code_assistant.py]
   ```
   
   You can include multiple files:
   ```
   > How can I improve these two files? [file1.py] [file2.py]
   ```

   You can specify line ranges to read only parts of a file:
   ```
   > What does this function do? [code_assistant.py:100-150]
   > Check lines 20-30 of [example.py:20-30]
   > Show me from line 50 onwards [file.py:50-]
   > Show me up to line 25 [file.py:-25]
   > What's on line 42? [file.py:42]
   ```

3. Use web search by prefixing your query with `search:` or `search `:
   ```
   > search: Python requests library documentation
   > search Python requests library documentation
   ```

4. Combine web search with file context:
   ```
   > search: How to optimize this function [example.py]
   ```

5. Include URLs in square brackets to fetch their content:
   ```
   > How to use the API described in [https://api.example.com/docs]
   ```

6. Edit files by prefixing your query with `edit:` or `edit `:
   ```
   > edit: [example.py] to add error handling to the parse_json function
   > edit [example.py] to add error handling to the parse_json function
   ```
   You'll see a diff of proposed changes and be asked to confirm before saving.

   If the file doesn't exist, you'll be prompted to create it:
   ```
   > edit: [new_file.py] to create a hello world function
   ```
   This will create the file (and any necessary directories) and then proceed with the edit.

7. Create new empty files by prefixing your query with `create:` or `create `:
   ```
   > create: [new_file.py]
   > create: [src/utils/helper.py]
   ```
   You'll be prompted to confirm before creating the file. If the file already exists, 
   you'll be asked if you want to overwrite it with an empty file.

8. Run commands by prefixing your query with `run:` or `run `:
   ```
   > run: the tests for this project
   > run the tests for this project
   ```
   The LLM will suggest a command based on your description, or you can specify:
   ```
   > run: 'python example.py'
   > run 'python example.py'
   ```
   
   You can include file context to help the LLM suggest more appropriate commands:
   ```
   > run: [main.py] to test this script
   ```
   
   You can also specify line ranges to focus on specific parts of files:
   ```
   > run: [main.py:50-100] to test this function
   ```
   
   All commands require confirmation before execution for safety.

9. Change models by prefixing your query with `model:` or `model `:
   ```
   > model: llama3
   > model codellama
   ```

10. Toggle AI thinking display with special commands:
   ```
   > thinking:on
   > thinking:off
   > thinking:length 2000
   ```

11. Adjust the timeout for LLM operations using the timeout command:
   ```
   > timeout:30
   > timeout:60
   > timeout:500
   ```
   Users with slower hardware or those using larger models may need to increase the timeout value to prevent operations from being cut off prematurely.

12. Combine all features as needed:
   ```
   > search: How to implement better error handling [search_test.py] [https://docs.python.org/3/library/]
   > What's wrong with this function? [buggy.py:25-50]
   > edit: [utils.py:100-150] to optimize the data processing function
   > run: 'python test.py' after looking at [test.py:10-30]
   > create: [new_module.py]
   ```

13. Use project planning for complex tasks:
   ```
   > plan: Create a Flask API with endpoints for user authentication
   > plan: Add unit tests for [app.py] functions
   > vibecode: Refactor the database connection in [db.py] to use connection pooling
   ```

14. Type `exit` to quit the application.

## Thinking Blocks Feature

The Thinking Blocks feature allows the AI assistant to include its reasoning process in responses while keeping it hidden by default. This helps maintain clean responses while providing the option to see the AI's thought process when needed.

### Thinking Blocks Commands

- `thinking:on` or `thinking on` - Show thinking blocks in responses
- `thinking:off` or `thinking off` - Hide thinking blocks in responses (default)
- `thinking:length N` or `thinking length N` - Set the maximum length of thinking blocks to N characters

### Example Usage

```
> thinking:on
Thinking display is now ON

> What is the factorial function?
🤖 Assistant:
<thinking>
The factorial function is a mathematical function that multiplies a number by all the positive integers less than it.
For example, factorial of 5 (written as 5!) is 5 × 4 × 3 × 2 × 1 = 120.
It's commonly used in combinatorics, probability, and other areas of mathematics.
</thinking>

The factorial function (denoted as n!) multiplies a positive integer by all positive integers less than it.

For example:
- 5! = 5 × 4 × 3 × 2 × 1 = 120
- 3! = 3 × 2 × 1 = 6
- 1! = 1
- 0! is defined as 1

It's commonly used in combinatorics, probability theory, and many other areas of mathematics and computer science.

> thinking:off
Thinking display is now OFF
```

## Partial File Reading Feature

The Partial File Reading feature allows you to specify line ranges when including files in your queries. This helps focus the AI's attention on specific parts of a file, which is particularly useful for large files or when you only need help with a specific function or section.

### Line Range Syntax

You can specify line ranges using the following syntax in square brackets:

- `[filename:start-end]` - Read lines from `start` to `end` (inclusive)
- `[filename:start-]` - Read lines from `start` to the end of the file
- `[filename:-end]` - Read lines from the beginning of the file to `end`
- `[filename:line]` - Read just the specified line

Line numbers are 1-indexed (the first line is line 1).

### Example Usage

```
> What does this function do? [code_assistant.py:100-150]
```
This reads only lines 100-150 of code_assistant.py and asks the AI about the function in that range.

```
> Check for bugs in the calculate_average function [math_utils.py:75-100]
```
This focuses the AI on just the calculate_average function in lines 75-100.

```
> Show me from line 50 onwards [file.py:50-]
```
This reads the file from line 50 to the end.

```
> Show me up to line 25 [file.py:-25]
```
This reads the file from the beginning to line 25.

```
> What's on line 42? [file.py:42]
```
This reads just line 42 of the file.

### Benefits

- **Reduced Token Usage**: By including only relevant parts of files, you use fewer tokens in the context window.
- **Focused Responses**: The AI can focus on specific sections without being distracted by irrelevant code.
- **Better Performance**: Processing smaller chunks of code can lead to more accurate and faster responses.
- **Easier Debugging**: You can target specific functions or code blocks that need attention.

## Safety Features

The assistant includes several safety measures:
- File edits always require user confirmation
- A backup is created before modifying any file (as filename.bak)
- Colored diffs show exactly what changes will be made
- Commands are checked against a list of safe prefixes
- Potentially dangerous commands trigger extra safety warnings
- All commands require explicit user confirmation

## Configuration

You can modify the default settings in the `code_assistant.py` file:

- `DEFAULT_MODEL`: Change the default Ollama model
- `MAX_SEARCH_RESULTS`: Adjust the number of search results included (default: 5)
- `MAX_URL_CONTENT_LENGTH`: Limit the amount of content fetched from URLs (default: 10000 characters)
- `SHOW_THINKING`: Control whether thinking blocks are shown (default: False)
- `MAX_THINKING_LENGTH`: Set the maximum length of thinking blocks (default: 5000 characters)
- `DEFAULT_TIMEOUT`: Set the default timeout value for LLM operations (default: 500 seconds)
- `SAFE_COMMAND_PREFIXES`: List of command prefixes considered safe to execute
- `DANGEROUS_COMMANDS`: List of potentially dangerous command elements that trigger warnings

## Notes

- The application automatically connects to the Ollama server running at `localhost:11434`.
- All processing happens locally on your machine, ensuring privacy.
- Web searches are conducted through DuckDuckGo, which doesn't track users.
- The conversation history is maintained for context but is not saved between sessions.
- URL content is filtered to extract useful text and truncated if too long.
- Command suggestions are based on your description and the files in your directory.
- Thinking blocks are hidden by default but can be shown with the `thinking:on` command.
- Partial file reading allows you to focus the LLM on specific parts of a file, which can help reduce token usage and get more targeted responses.
- The default timeout for LLM operations is 500 seconds, which can be adjusted using the `timeout:N` command if you're experiencing timeouts with larger models or complex queries.

## Privacy Considerations

This tool is designed with privacy in mind:
- Uses a local LLM through Ollama instead of cloud-based APIs
- Uses DuckDuckGo for web searches, which doesn't track users
- All processing happens locally on your machine
- No data is stored beyond the current session

## Project Structure

- `code_assistant.py`: Main program file
- `benchmark.py`: Performance benchmarking tool
- `requirements.txt`: Required Python packages
- `examples/`: Example files for demonstrating the assistant's capabilities
- `tests/`: Test suite for the project
  - `test_thinking_blocks.py`: Tests for the thinking blocks feature 

## File Creation Feature

The File Creation feature allows you to create new empty files with a simple command. This is useful when you want to start a new file from scratch or create placeholder files for a project structure.

### Usage

To create a new file, use the `create:` prefix followed by the file path in square brackets:

```
> create: [new_file.py]
```

You'll be prompted to confirm before the file is created:

```
Create 'new_file.py'? (y/n): y
Created 'new_file.py'.
```

If the file already exists, you'll be asked if you want to overwrite it:

```
File 'existing_file.py' already exists.
Overwrite with an empty file? (y/n): n
File creation cancelled for 'existing_file.py'.
```

You can create files in directories that don't exist yet, and the necessary directories will be created automatically:

```
> create: [src/utils/helper.py]
Create 'src/utils/helper.py'? (y/n): y
Created 'src/utils/helper.py'.
```

You can also create multiple files at once:

```
> create: [file1.py] [file2.py]
```

### Enhanced Edit Functionality

The Edit functionality has been enhanced to handle new files as well. If you try to edit a file that doesn't exist, you'll be prompted to create it:

```
> edit: [new_file.py] to add a hello world function
File 'new_file.py' doesn't exist. Create it? (y/n): y
Created 'new_file.py'.
```

This allows you to create and edit files in a single step, making it easier to start new files with content.

## Enhanced Run Functionality

The Run functionality has been enhanced to include file context when suggesting commands. This helps the LLM understand what you're trying to do and suggest more appropriate commands.

### Usage

To run a command with file context, include file paths in square brackets:

```
> run: [main.py] to test this script
```

The LLM will read the content of the file and suggest a command based on it:

```
🤖 Assistant:
Based on the content of main.py, I suggest running the script with Python:

python main.py

This will execute the script and display its output.

Suggested command:
python main.py

Run this command? (y/n): y
```

You can include multiple files to provide more context:

```
> run: [test_file.py] [main.py] to run tests on the main file
```

You can also specify line ranges to focus on specific parts of files:

```
> run: [main.py:50-100] to test this function
```

This is particularly useful when you want to run a specific test or function within a larger file.

### Safety Features

The Run functionality includes several safety measures:
- Commands are checked against a list of safe prefixes
- Potentially dangerous commands trigger extra safety warnings with specific reasons
- All commands require explicit user confirmation before execution
- Command output is displayed and added to the conversation history

## Plan/Vibecode Feature

The Plan/Vibecode feature allows you to create and execute project plans with the LLM. This is useful for breaking down complex tasks into smaller, executable steps.

### Usage

To create and execute a project plan, use the `plan:` or `vibecode:` prefix followed by a description of the plan:

```
> plan: Create a simple Python script that prints 'Hello, World!' and run it to verify
> vibecode: Build a basic web server with Node.js and Express
```

The LLM will break down your request into executable steps in a standardized JSON format. These steps can include:
- Creating files
- Writing code to files
- Editing existing files
- Running commands
- Verifying command outputs

Each step is displayed and requires confirmation before execution, giving you full control over the process.

You can include file context to help the LLM understand the existing code:
```
> plan: Add more error handling to this API endpoint [api.py]
```

The plan will be executed interactively, allowing you to:
- Review each step before execution
- Skip steps you don't want to execute
- Save the plan to a JSON file for later use

## License

This project is licensed under the MIT License (c) 2025 Aditya Bawankule. See the [LICENSE](./LICENSE) file for details.
