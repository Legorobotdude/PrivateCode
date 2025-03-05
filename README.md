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

3. Use web search by prefixing your query with `search:`:
   ```
   > search: Python requests library documentation
   ```

4. Combine web search with file context:
   ```
   > search: How to optimize this function [example.py]
   ```

5. Include URLs in square brackets to fetch their content:
   ```
   > How to use the API described in [https://api.example.com/docs]
   ```

6. Edit files by prefixing your query with `edit:`:
   ```
   > edit: [example.py] to add error handling to the parse_json function
   ```
   You'll see a diff of proposed changes and be asked to confirm before saving.

7. Run commands by prefixing your query with `run:`:
   ```
   > run: the tests for this project
   ```
   The LLM will suggest a command based on your description, or you can specify:
   ```
   > run: 'python example.py'
   ```
   All commands require confirmation before execution for safety.

8. Combine all features as needed:
   ```
   > search: How to implement better error handling [search_test.py] [https://docs.python.org/3/library/]
   ```

9. Type `exit` to quit the application.

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
- `SAFE_COMMAND_PREFIXES`: List of command prefixes considered safe to execute
- `DANGEROUS_COMMANDS`: List of potentially dangerous command elements that trigger warnings

## Notes

- The application automatically connects to the Ollama server running at `localhost:11434`.
- All processing happens locally on your machine, ensuring privacy.
- Web searches are conducted through DuckDuckGo, which doesn't track users.
- The conversation history is maintained for context but is not saved between sessions.
- URL content is filtered to extract useful text and truncated if too long.
- Command suggestions are based on your description and the files in your directory.

## Privacy Considerations

This tool is designed with privacy in mind:
- Uses a local LLM through Ollama instead of cloud-based APIs
- Uses DuckDuckGo for web searches, which doesn't track users
- All processing happens locally on your machine
- No data is stored beyond the current session 