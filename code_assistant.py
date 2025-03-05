#!/usr/bin/env python3
"""
Local LLM-powered Coding Assistant

This tool connects to a local Ollama instance to provide coding assistance
with context from files in your current directory. It can also search the web
for information and include it in the context for the LLM. The assistant can now
edit files and execute commands with user confirmation.
"""

import requests
import re
import json
import sys
import os
import difflib
import subprocess
from bs4 import BeautifulSoup
from urllib.parse import quote_plus, urlparse
from shutil import copyfile
from colorama import init, Fore, Style

# Initialize colorama for cross-platform color support
init()

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "codellama"  # Change to your preferred model
MAX_SEARCH_RESULTS = 5      # Maximum number of search results to include
MAX_URL_CONTENT_LENGTH = 10000  # Maximum characters to include from URL content

# Command execution safety
SAFE_COMMAND_PREFIXES = ["python", "python3", "node", "npm", "git", "ls", "dir", "cd", "type", "cat", "make", "dotnet", "gradle", "mvn", "cargo", "rustc", "go", "test", "echo"]
DANGEROUS_COMMANDS = ["rm", "del", "sudo", "chmod", "chown", "mv", "cp", "rmdir", "rd", "format", "mkfs", "dd", ">", ">>"]


def check_ollama_connection():
    """Verify the Ollama server is running and accessible."""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("Successfully connected to Ollama server.")
            models = response.json().get("models", [])
            if models:
                available_models = [model.get("name") for model in models]
                print(f"Available models: {', '.join(available_models)}")
            return True
        else:
            print(f"Error connecting to Ollama: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to Ollama server: {e}")
        print("Please ensure Ollama is running on your system.")
        return False


def read_file_content(file_path):
    """Read content from a file, handling potential errors."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Warning: File '{file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error reading file '{file_path}': {e}")
        return None


def write_file_content(file_path, content, create_backup=True):
    """Write content to a file, optionally creating a backup first."""
    try:
        # Create a backup if the file exists and backup is requested
        if os.path.exists(file_path) and create_backup:
            backup_path = f"{file_path}.bak"
            try:
                copyfile(file_path, backup_path)
                print(f"Created backup at {backup_path}")
            except Exception as e:
                print(f"Warning: Could not create backup: {e}")
        
        # Write the new content
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        return True
    except Exception as e:
        print(f"Error writing to file '{file_path}': {e}")
        return False


def generate_colored_diff(original, modified, file_path):
    """Generate a colored diff between original and modified content."""
    diff = difflib.unified_diff(
        original.splitlines(),
        modified.splitlines(),
        fromfile=f'a/{file_path}',
        tofile=f'b/{file_path}',
        lineterm=''
    )
    
    colored_diff = []
    for line in diff:
        if line.startswith('+'):
            colored_diff.append(f"{Fore.GREEN}{line}{Style.RESET_ALL}")
        elif line.startswith('-'):
            colored_diff.append(f"{Fore.RED}{line}{Style.RESET_ALL}")
        elif line.startswith('^'):
            colored_diff.append(f"{Fore.BLUE}{line}{Style.RESET_ALL}")
        elif line.startswith('@'):
            colored_diff.append(f"{Fore.CYAN}{line}{Style.RESET_ALL}")
        else:
            colored_diff.append(line)
    
    return '\n'.join(colored_diff)


def get_edit_file_paths(query):
    """Extract file paths from an edit query."""
    # Extract file paths in square brackets
    pattern = r'\[([^\]]+)\]'
    matches = re.findall(pattern, query)
    
    # If no matches found, return the whole query and empty list
    if not matches:
        return query, []
    
    # Remove the file paths from the query to get the instruction
    clean_query = re.sub(pattern, '', query).strip()
    return clean_query, matches


def is_safe_command(command):
    """Check if a command is likely safe to execute."""
    command_lower = command.lower()
    
    # Check for dangerous commands
    for dangerous in DANGEROUS_COMMANDS:
        if dangerous in command_lower:
            return False, f"Command contains potentially dangerous operation: '{dangerous}'"
    
    # Check for safe prefixes
    for prefix in SAFE_COMMAND_PREFIXES:
        if command_lower.startswith(prefix):
            return True, None
    
    # If no safe prefix is found, consider it potentially unsafe
    return False, "Command does not start with a recognized safe prefix"


def execute_command(command):
    """Execute a command and return its output."""
    try:
        # Run the command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        # Prepare output
        output = ""
        if result.stdout:
            output += f"Standard Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"Standard Error:\n{result.stderr}\n"
        
        output += f"Exit Code: {result.returncode}"
        return output
    except Exception as e:
        return f"Error executing command: {e}"


def fetch_url_content(url):
    """Fetch and extract text content from a URL."""
    try:
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            # Try to determine content type
            content_type = response.headers.get('Content-Type', '').lower()
            
            # If it's HTML, parse with BeautifulSoup
            if 'text/html' in content_type:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                
                # Get text and clean it up
                text = soup.get_text(separator='\n')
                lines = (line.strip() for line in text.splitlines())
                text = '\n'.join(line for line in lines if line)
                
                # Truncate if too long
                if len(text) > MAX_URL_CONTENT_LENGTH:
                    text = text[:MAX_URL_CONTENT_LENGTH] + "... [content truncated]"
                
                return text
            else:
                # For non-HTML content, just return the raw text
                text = response.text
                if len(text) > MAX_URL_CONTENT_LENGTH:
                    text = text[:MAX_URL_CONTENT_LENGTH] + "... [content truncated]"
                return text
        else:
            return f"Failed to fetch {url}: HTTP status {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Failed to fetch {url}: {e}"
    except Exception as e:
        return f"Error processing {url}: {e}"


def duckduckgo_search(query, num_results=MAX_SEARCH_RESULTS):
    """Perform a web search using DuckDuckGo and return structured results."""
    print(f"Searching the web for: {query}")
    
    try:
        # Use DuckDuckGo HTML search instead of API since their API is limited
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Search failed: HTTP status {response.status_code}")
            return []
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # Find search result elements
        for result in soup.select('.result'):
            title_elem = result.select_one('.result__title')
            snippet_elem = result.select_one('.result__snippet')
            url_elem = result.select_one('.result__url')
            
            if title_elem and snippet_elem:
                title = title_elem.get_text().strip()
                snippet = snippet_elem.get_text().strip()
                
                # Get URL from href if available
                url = ""
                if url_elem:
                    url = url_elem.get_text().strip()
                elif title_elem.a and title_elem.a.get('href'):
                    href = title_elem.a.get('href')
                    if href.startswith('/'):
                        # Extract URL from DuckDuckGo redirect
                        match = re.search(r'uddg=([^&]+)', href)
                        if match:
                            url = match.group(1)
                
                results.append({
                    'title': title,
                    'description': snippet,
                    'url': url
                })
                
                if len(results) >= num_results:
                    break
        
        print(f"Found {len(results)} search results.")
        return results
    
    except Exception as e:
        print(f"Error during web search: {e}")
        return []


def extract_file_paths_and_urls(query):
    """Extract file paths and URLs enclosed in square brackets from the query."""
    pattern = r'\[([^\]]+)\]'
    matches = re.findall(pattern, query)
    
    # Remove the bracketed content from the query
    clean_query = re.sub(pattern, '', query).strip()
    
    # Separate file paths and URLs
    file_paths = []
    urls = []
    
    for match in matches:
        # Check if it's a URL (has domain-like structure)
        if match.startswith(('http://', 'https://')) or '.' in match and '/' in match:
            urls.append(match)
        else:
            file_paths.append(match)
    
    return clean_query, file_paths, urls


def is_search_query(query):
    """Check if the query is a search request."""
    return query.lower().startswith('search:')


def is_edit_query(query):
    """Check if the query is a file edit request."""
    return query.lower().startswith('edit:')


def is_run_query(query):
    """Check if the query is a command execution request."""
    return query.lower().startswith('run:')


def extract_search_query(query):
    """Extract the search term from a search query."""
    if is_search_query(query):
        # Remove 'search:' prefix and trim whitespace
        return query[7:].strip()
    return query


def extract_edit_query(query):
    """Extract the edit instruction from an edit query."""
    if is_edit_query(query):
        # Remove 'edit:' prefix and trim whitespace
        return query[5:].strip()
    return query


def extract_run_query(query):
    """Extract the command or description from a run query."""
    if is_run_query(query):
        # Remove 'run:' prefix and trim whitespace
        return query[4:].strip()
    return query


def extract_specific_command(query):
    """Extract a specific command enclosed in single quotes."""
    # Look for text enclosed in single quotes
    match = re.search(r"'([^']*)'", query)
    if match:
        return match.group(1)
    return None


def get_file_list():
    """Get a list of files in the current directory."""
    try:
        files = os.listdir('.')
        # Filter out hidden files and directories
        files = [f for f in files if not f.startswith('.')]
        return files
    except Exception as e:
        print(f"Error listing files: {e}")
        return []


def get_ollama_response(history, model=DEFAULT_MODEL):
    """Send conversation history to Ollama and get a response."""
    try:
        payload = {
            "model": model,
            "messages": history,
            "stream": False  # We're not using streaming for simplicity
        }
        
        response = requests.post(OLLAMA_API_URL, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return result.get("message", {}).get("content", "No response from the model.")
        else:
            return f"Error: Received status code {response.status_code} from Ollama API."
    
    except requests.exceptions.RequestException as e:
        return f"Error communicating with Ollama API: {e}"


def extract_modified_content(response, file_path):
    """Extract the modified content from the LLM's response."""
    # Look for content after "Modified [file_path]:" or similar patterns
    patterns = [
        f"Modified {file_path}:\n",
        f"MODIFIED {file_path}:\n",
        f"Modified File {file_path}:\n",
        f"Modified content of {file_path}:\n",
        f"Updated {file_path}:\n",
        "```python\n",  # For code blocks
        "```\n"         # For generic code blocks
    ]
    
    # First, try to find structured content based on patterns
    for pattern in patterns:
        if pattern in response:
            parts = response.split(pattern, 1)
            if len(parts) > 1:
                content = parts[1]
                
                # If this is a code block, find the closing code block marker
                if pattern.startswith("```"):
                    if "```" in content:
                        content = content.split("```", 1)[0].strip()
                
                # Otherwise, look for other patterns that might indicate the end of content
                else:
                    # Check for other start patterns that might appear later (indicating different sections)
                    end_markers = [
                        "\n\nExplanation:",
                        "\n\nHere's what changed:",
                        "\n\nThe changes include:",
                        "\n\nI've made the following changes:"
                    ]
                    
                    for marker in end_markers:
                        if marker in content:
                            content = content.split(marker, 1)[0]
                
                # Remove any trailing code block markers
                content = content.strip()
                if content.endswith("```"):
                    content = content[:-3].strip()
                
                return content
    
    # If we couldn't extract using patterns, try a more aggressive approach
    # to extract content between code blocks if present
    if "```" in response:
        code_blocks = response.split("```")
        # If we have at least one complete code block (opening and closing ```)
        if len(code_blocks) >= 3:
            # First element is before the opening ```, second is the content
            content = code_blocks[1]
            # Remove the language indicator if present (like "python")
            if "\n" in content:
                content = content.split("\n", 1)[1]
            return content.strip()
    
    # If no pattern matched, return the raw response with a warning
    print(f"{Fore.YELLOW}Warning: Could not identify modified content section. Using raw response.{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}The response might need cleanup before saving.{Style.RESET_ALL}")
    
    # Ask user if they want to see the raw response
    show_raw = input(f"{Fore.YELLOW}Do you want to see the raw response to manually extract content? (y/n): {Style.RESET_ALL}").lower()
    if show_raw == 'y' or show_raw == 'yes':
        print("\nRaw response:")
        print(response)
        
        # Give user option to manually extract content
        use_raw = input(f"{Fore.YELLOW}Do you want to use this raw response as the file content? (y/n): {Style.RESET_ALL}").lower()
        if use_raw != 'y' and use_raw != 'yes':
            return None
    
    return response


def extract_suggested_command(response):
    """Extract the suggested command from the LLM's response."""
    # Look for patterns indicating a command suggestion
    patterns = [
        "Suggested command: ",
        "Command: ",
        "Run: ",
        "Execute: "
    ]
    
    for pattern in patterns:
        if pattern in response:
            # Extract the command from the line containing the pattern
            lines = response.split('\n')
            for line in lines:
                if pattern in line:
                    command = line.split(pattern, 1)[1].strip()
                    # Remove any trailing punctuation or quotes
                    command = re.sub(r'["`\']$', '', command)
                    command = re.sub(r'^["`\']', '', command)
                    return command
    
    # If no pattern matched, extract the first line that looks like a command
    lines = response.split('\n')
    for line in lines:
        line = line.strip()
        if line and not line.startswith(('#', '//', '/*', '*', '<!--')):
            return line
    
    # If all else fails, return the raw response with a warning
    print(f"{Fore.YELLOW}Warning: Could not identify a command in the response.{Style.RESET_ALL}")
    return None


def main():
    """Main function to run the coding assistant."""
    print(f"{Fore.CYAN}🤖 Local LLM Coding Assistant 🤖{Style.RESET_ALL}")
    print(f"{Fore.CYAN}================================{Style.RESET_ALL}")
    print("Enter your coding questions and include file paths in square brackets.")
    print("Example: How can I improve this code? [main.py]")
    print()
    print("For web searches, prefix with 'search:' - Example: search: Python requests library")
    print("For file editing, prefix with 'edit:' - Example: edit: [main.py] to fix the function")
    print("For running commands, prefix with 'run:' - Example: run: the tests or run: 'python test.py'")
    print("Include URLs in brackets - Example: How to use this API? [https://api.example.com/docs]")
    print()
    print("Type 'exit' to quit.")
    print()
    
    # Check Ollama connection
    if not check_ollama_connection():
        print("Exiting due to connection issues with Ollama.")
        sys.exit(1)
    
    # Initialize conversation history
    conversation_history = []
    
    while True:
        # Get user input
        user_input = input(f"\n{Fore.GREEN}> {Style.RESET_ALL}")
        
        # Check for exit command
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye! 👋")
            break
        
        # Check query type
        search_mode = is_search_query(user_input)
        edit_mode = is_edit_query(user_input)
        run_mode = is_run_query(user_input)
        
        # Handle different query types
        if search_mode:
            handle_search_query(user_input, conversation_history)
        elif edit_mode:
            handle_edit_query(user_input, conversation_history)
        elif run_mode:
            handle_run_query(user_input, conversation_history)
        else:
            handle_regular_query(user_input, conversation_history)


def handle_search_query(user_input, conversation_history):
    """Handle search queries with DuckDuckGo."""
    # Extract the actual search query
    user_input = extract_search_query(user_input)
    print(f"Search mode enabled for: {user_input}")
    
    # Parse the query to extract file paths and URLs
    clean_query, file_paths, urls = extract_file_paths_and_urls(user_input)
    
    # Initialize sections for the prompt
    search_results_section = ""
    files_content_section = ""
    url_content_section = ""
    
    # Perform web search
    search_results = duckduckgo_search(clean_query)
    
    if search_results:
        search_results_section = "\nSearch Results:\n"
        for i, result in enumerate(search_results, 1):
            search_results_section += f"{i}. Title: {result['title']}\n"
            search_results_section += f"   Description: {result['description']}\n"
            search_results_section += f"   URL: {result['url']}\n\n"
    else:
        search_results_section = "\nNo search results found.\n"
    
    # Read file contents
    if file_paths:
        files_content_section = "\nFiles:\n"
        for file_path in file_paths:
            content = read_file_content(file_path)
            if content:
                files_content_section += f"File: {file_path}\nContent:\n{content}\n\n"
    
    # Fetch URL contents
    if urls:
        url_content_section = "\nURL Content:\n"
        for url in urls:
            content = fetch_url_content(url)
            if content:
                url_content_section += f"URL: {url}\nContent:\n{content}\n\n"
    
    # Construct user message
    user_message = f"Query: {clean_query}"
    
    # Add search results, file contents, and URL contents if available
    if search_results_section:
        user_message += search_results_section
    if files_content_section:
        user_message += files_content_section
    if url_content_section:
        user_message += url_content_section
    
    # Add the user message to the conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    # Print "Thinking..." to indicate processing
    print(f"\n{Fore.YELLOW}Thinking...{Style.RESET_ALL}\n")
    
    # Get response from Ollama
    assistant_response = get_ollama_response(conversation_history)
    
    # Display the response
    print(f"{Fore.CYAN}🤖 Assistant:{Style.RESET_ALL}\n{assistant_response}")
    
    # Add the assistant's response to the conversation history
    conversation_history.append({"role": "assistant", "content": assistant_response})


def handle_edit_query(user_input, conversation_history):
    """Handle file editing requests."""
    # Extract the edit instruction
    edit_instruction = extract_edit_query(user_input)
    
    # Get file paths from the instruction
    clean_instruction, file_paths = get_edit_file_paths(edit_instruction)
    
    if not file_paths:
        print(f"{Fore.RED}Error: No file specified for editing. Please use format: edit: [filename] instruction{Style.RESET_ALL}")
        return
    
    # Only edit one file at a time
    file_path = file_paths[0]
    print(f"Edit mode enabled for file: {file_path}")
    
    # Read the file content
    original_content = read_file_content(file_path)
    if not original_content:
        return
    
    # Construct prompt for the LLM
    prompt = f"User wants to {clean_instruction} in file {file_path}.\n\n"
    prompt += f"Current content of {file_path}:\n"
    prompt += original_content + "\n\n"
    prompt += f"Please provide the modified content of {file_path} after making the required changes.\n"
    prompt += f"Format your response as:\nModified {file_path}:\n[entire file content with changes]\n"
    prompt += "Only include the modified file content, not explanations or additional context.\n"
    prompt += "Do not include examples, other files, or file content that was provided in the conversation history.\n"
    prompt += "Do not include markdown formatting like triple backticks (```) in your response."
    
    # Add the edit request to conversation history
    conversation_history.append({"role": "user", "content": prompt})
    
    # Print "Thinking..." to indicate processing
    print(f"\n{Fore.YELLOW}Thinking about file edits...{Style.RESET_ALL}\n")
    
    # Get response from Ollama
    assistant_response = get_ollama_response(conversation_history)
    
    # Extract the modified content
    modified_content = extract_modified_content(assistant_response, file_path)
    
    # If we couldn't extract the content or user chose not to use raw content
    if modified_content is None:
        print(f"{Fore.RED}Edit canceled. No changes made to {file_path}{Style.RESET_ALL}")
        return
    
    # Generate diff and display it
    if modified_content and modified_content != original_content:
        print(f"\n{Fore.CYAN}Proposed changes to {file_path}:{Style.RESET_ALL}")
        colored_diff = generate_colored_diff(original_content, modified_content, file_path)
        print(colored_diff)
        
        # Ask for confirmation
        confirm = input(f"\n{Fore.YELLOW}Do you want to save these changes? (y/n): {Style.RESET_ALL}").lower()
        if confirm == 'y' or confirm == 'yes':
            if write_file_content(file_path, modified_content):
                print(f"{Fore.GREEN}Changes saved to {file_path}{Style.RESET_ALL}")
                
                # Add a record of the successful edit to the conversation history
                edit_summary = f"I've modified file {file_path} as requested, applying the changes shown in the diff."
                conversation_history.append({"role": "assistant", "content": edit_summary})
            else:
                print(f"{Fore.RED}Failed to save changes to {file_path}{Style.RESET_ALL}")
                
                # Add a record of the failed edit to the conversation history
                conversation_history.append({
                    "role": "assistant", 
                    "content": f"I attempted to modify file {file_path} but encountered an error when saving the changes."
                })
        else:
            print(f"{Fore.RED}Edit canceled. No changes made to {file_path}{Style.RESET_ALL}")
            
            # Add a record of the canceled edit to the conversation history
            conversation_history.append({
                "role": "assistant", 
                "content": f"I suggested changes to {file_path} but they were not applied."
            })
    else:
        print(f"{Fore.YELLOW}No changes were made to the file.{Style.RESET_ALL}")
        
        # Add a record to the conversation history
        conversation_history.append({
            "role": "assistant", 
            "content": f"I analyzed {file_path} but did not make any changes."
        })


def handle_run_query(user_input, conversation_history):
    """Handle command execution requests."""
    # Extract the run instruction
    run_instruction = extract_run_query(user_input)
    
    # Check if this is a specific command (enclosed in quotes)
    specific_command = extract_specific_command(run_instruction)
    
    if specific_command:
        # User provided a specific command to run
        command = specific_command
        print(f"Executing specific command: {command}")
    else:
        # Ask LLM to suggest a command
        file_list = get_file_list()
        file_list_str = ", ".join(file_list[:20])  # Limit to 20 files to avoid overloading the prompt
        
        # Construct prompt for command suggestion
        prompt = f"User wants to run: {run_instruction}.\n\n"
        prompt += f"Current directory contains these files: {file_list_str}\n\n"
        prompt += "Please suggest a command to run based on the user's request.\n"
        prompt += "Format your response as:\nSuggested command: [command]"
        
        # Add the run request to conversation history
        conversation_history.append({"role": "user", "content": prompt})
        
        # Print "Thinking..." to indicate processing
        print(f"\n{Fore.YELLOW}Thinking about what command to run...{Style.RESET_ALL}\n")
        
        # Get response from Ollama
        assistant_response = get_ollama_response(conversation_history)
        
        # Extract the suggested command
        command = extract_suggested_command(assistant_response)
        
        if not command:
            print(f"{Fore.RED}Error: Could not determine a command to run.{Style.RESET_ALL}")
            return
        
        print(f"\n{Fore.CYAN}Suggested command:{Style.RESET_ALL} {command}")
        
        # Add the suggestion to conversation history
        conversation_history.append({
            "role": "assistant", 
            "content": f"I suggest running the command: {command}"
        })
    
    # Check command safety
    is_safe, reason = is_safe_command(command)
    
    if not is_safe:
        print(f"{Fore.RED}Warning: {reason}{Style.RESET_ALL}")
        confirm = input(f"{Fore.RED}This command seems unsafe. Are you sure you want to proceed? (y/n): {Style.RESET_ALL}").lower()
        if confirm != 'y' and confirm != 'yes':
            print(f"{Fore.YELLOW}Command execution canceled.{Style.RESET_ALL}")
            return
    else:
        # Ask for confirmation
        confirm = input(f"\n{Fore.YELLOW}Do you want to run this command? (y/n): {Style.RESET_ALL}").lower()
        if confirm != 'y' and confirm != 'yes':
            print(f"{Fore.YELLOW}Command execution canceled.{Style.RESET_ALL}")
            return
    
    # Execute the command
    print(f"{Fore.CYAN}Executing: {command}{Style.RESET_ALL}")
    output = execute_command(command)
    
    # Display the output
    print(f"\n{Fore.CYAN}Command Output:{Style.RESET_ALL}\n{output}")
    
    # Add the execution result to conversation history
    conversation_history.append({
        "role": "assistant", 
        "content": f"I executed the command: {command}\n\nOutput:\n{output}"
    })


def handle_regular_query(user_input, conversation_history):
    """Handle regular information or analysis queries."""
    # Parse the query to extract file paths and URLs
    clean_query, file_paths, urls = extract_file_paths_and_urls(user_input)
    
    # Initialize sections for the prompt
    files_content_section = ""
    url_content_section = ""
    
    # Read file contents
    if file_paths:
        files_content_section = "\nFiles:\n"
        for file_path in file_paths:
            content = read_file_content(file_path)
            if content:
                files_content_section += f"File: {file_path}\nContent:\n{content}\n\n"
    
    # Fetch URL contents
    if urls:
        url_content_section = "\nURL Content:\n"
        for url in urls:
            content = fetch_url_content(url)
            if content:
                url_content_section += f"URL: {url}\nContent:\n{content}\n\n"
    
    # Construct user message
    user_message = f"Query: {clean_query}"
    
    # Add file contents and URL contents if available
    if files_content_section:
        user_message += files_content_section
    if url_content_section:
        user_message += url_content_section
    
    # Add the user message to the conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    # Print "Thinking..." to indicate processing
    print(f"\n{Fore.YELLOW}Thinking...{Style.RESET_ALL}\n")
    
    # Get response from Ollama
    assistant_response = get_ollama_response(conversation_history)
    
    # Display the response
    print(f"{Fore.CYAN}🤖 Assistant:{Style.RESET_ALL}\n{assistant_response}")
    
    # Add the assistant's response to the conversation history
    conversation_history.append({"role": "assistant", "content": assistant_response})


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
        sys.exit(0) 