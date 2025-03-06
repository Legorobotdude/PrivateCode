# Local LLM Coding Assistant

A terminal-based coding assistant that uses local Large Language Models (LLMs) via Ollama to provide coding help and answer programming questions. The assistant can also search the web for information while maintaining privacy, edit files, and execute commands with user confirmation.

## Features

- Interactive terminal interface
- Context-aware coding assistance
- File inclusion for code context
- Web search capabilities with DuckDuckGo
- URL content extraction for reference
- Intelligent file editing with diff preview
- Safe command execution with LLM suggestions
- Persistent conversation history
- Locally hosted LLM (no data sent to external services)
- AI thinking blocks with configurable display options

## Prerequisites

- Python 3.6+
- [Ollama](https://ollama.ai/) installed and running locally
- A code LLM model pulled in Ollama (e.g., codellama, llama2, mixtral)
- Internet connection (for web search functionality)

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

7. Run commands by prefixing your query with `run:` or `run `:
   ```
   > run: the tests for this project
   > run the tests for this project
   ```
   The LLM will suggest a command based on your description, or you can specify:
   ```
   > run: 'python example.py'
   > run 'python example.py'
   ```
   All commands require confirmation before execution for safety.

8. Change models by prefixing your query with `model:` or `model `:
   ```
   > model: llama3
   > model codellama
   ```

9. Toggle AI thinking display with special commands:
   ```
   > thinking:on
   > thinking:off
   > thinking:length 2000
   ```

10. Combine all features as needed:
   ```
   > search: How to implement better error handling [search_test.py] [https://docs.python.org/3/library/]
   ```

11. Type `exit` to quit the application.

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