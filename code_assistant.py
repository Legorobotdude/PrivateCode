#!/usr/bin/env python3
"""
Code Assistant - A command-line interface for interacting with Ollama models

This script provides a command-line interface for interacting with Ollama models,
allowing users to ask questions, search the web, edit files, and run commands.

Features:
- Chat with Ollama models
- Search the web for information
- Edit files with AI assistance
- Run commands with AI guidance
- Switch between different Ollama models
- Display or hide AI "thinking" process
- Read specific line ranges from files using [filename:start-end] syntax

Usage:
  python code_assistant.py [query]

Examples:
  python code_assistant.py "Explain how async/await works in JavaScript"
  python code_assistant.py "Search: latest developments in quantum computing"
  python code_assistant.py "Edit: [main.py] Add error handling to the main function"
  python code_assistant.py "Run: Write a script to sort files by extension"
  python code_assistant.py "Model: llama3"
  python code_assistant.py "Show only lines 10-20 of my file [myfile.py:10-20]"
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
DEFAULT_MODEL = "qwq"  # Change to your preferred model
CURRENT_MODEL = DEFAULT_MODEL  # Track the currently selected model
MAX_SEARCH_RESULTS = 5      # Maximum number of search results to include
MAX_URL_CONTENT_LENGTH = 10000  # Maximum characters to include from URL content
SHOW_THINKING = False  # Default to hiding thinking blocks
MAX_THINKING_LENGTH = 5000  # Maximum length of thinking block to display

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


def detect_file_encoding(file_path):
    """Detect the encoding of a file.
    
    Returns:
        tuple: (encoding, bom) where bom is True if the file has a BOM
    """
    # Try to detect encoding with these common types
    encodings_to_try = ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
    
    # First check for BOM using binary mode
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(4)  # Read first 4 bytes to check for BOM
            # Check for BOM markers
            if raw.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                return 'utf-8-sig', True
            elif raw.startswith(b'\xff\xfe'):  # UTF-16 LE BOM
                return 'utf-16-le', True
            elif raw.startswith(b'\xfe\xff'):  # UTF-16 BE BOM
                return 'utf-16-be', True
    except Exception:
        pass  # Fall back to detection by reading the file
        
    # Try each encoding
    for encoding in encodings_to_try:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
                # If we got here, the encoding worked
                return encoding, encoding.endswith('-sig')
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    
    # Default to UTF-8 if we couldn't detect
    return 'utf-8', False


def read_file_content(file_path, start_line=None, end_line=None):
    """
    Read content from a file, handling potential errors and encoding issues.
    
    Args:
        file_path (str): Path to the file to read
        start_line (int, optional): Starting line number (1-indexed)
        end_line (int, optional): Ending line number (1-indexed)
    
    Returns:
        str: File content or None if file not found or error occurs
    """
    if not os.path.exists(file_path):
        print(f"Warning: File '{file_path}' not found.")
        return None
        
    try:
        # Detect the encoding
        encoding, has_bom = detect_file_encoding(file_path)
        
        # Read the file with the detected encoding
        with open(file_path, 'r', encoding=encoding) as file:
            if start_line is None and end_line is None:
                # Read the entire file
                content = file.read()
            else:
                # Read specific lines
                lines = file.readlines()
                
                # Adjust for 1-indexed input to 0-indexed list
                start_idx = max(0, (start_line or 1) - 1)
                # If end_line is None, read to the end of the file
                end_idx = min(len(lines), end_line) if end_line is not None else len(lines)
                
                # Extract the requested lines
                selected_lines = lines[start_idx:end_idx]
                content = ''.join(selected_lines)
                
                # Add a note about the line range
                line_info = f"Lines {start_line or 1}-{end_line or len(lines)} of {len(lines)} total lines"
                content = f"--- {line_info} ---\n{content}"
            
        # Let the user know if we're using a non-standard encoding
        if encoding != 'utf-8' and encoding != 'utf-8-sig':
            print(f"Note: File '{file_path}' was read with {encoding} encoding.")
            
        return content
            
    except Exception as e:
        # If all else fails, try binary mode as a last resort
        try:
            with open(file_path, 'rb') as file:
                binary_content = file.read()
                # Try to decode as latin-1 which can handle any byte value
                print(f"Warning: Using binary fallback for '{file_path}'")
                return binary_content.decode('latin-1', errors='replace')
        except Exception as e2:
            print(f"Error reading file '{file_path}': {e2}")
            return None


def write_file_content(file_path, content, create_backup=True):
    """Write content to a file, preserving the original encoding."""
    try:
        # Get the file's original encoding if it exists
        original_encoding = 'utf-8'  # Default encoding
        has_bom = False
        
        if os.path.exists(file_path):
            # Detect the existing encoding
            original_encoding, has_bom = detect_file_encoding(file_path)
            
            # Create a backup if requested
            if create_backup:
                backup_path = f"{file_path}.bak"
                try:
                    copyfile(file_path, backup_path)
                    print(f"Created backup at {backup_path}")
                except Exception as e:
                    print(f"Warning: Could not create backup: {e}")
        
        # Write with detected encoding
        with open(file_path, 'w', encoding=original_encoding) as file:
            file.write(content)
            
        # Log the encoding used
        if original_encoding != 'utf-8' and original_encoding != 'utf-8-sig':
            print(f"Note: File '{file_path}' was written with {original_encoding} encoding to match the original.")
            
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
    """
    Extract file paths from an edit query.
    
    This function is maintained for backward compatibility.
    It uses extract_file_paths_and_urls internally and returns just the file paths.
    """
    # Use the new extract_file_paths_and_urls function
    clean_query, file_items, _ = extract_file_paths_and_urls(query)
    
    # Extract just the file paths from the file items
    file_paths = []
    for item in file_items:
        if isinstance(item, tuple):
            file_paths.append(item[0])
        else:
            file_paths.append(item)
    
    return file_paths


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
                    'snippet': snippet,
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
    """
    Extract file paths and URLs enclosed in square brackets from the query.
    Supports line range specifications in the format [filename:start-end], [filename:start-], or [filename:-end].
    """
    pattern = r'\[([^\]]+)\]'
    matches = re.findall(pattern, query)
    
    # Remove the bracketed content from the query
    clean_query = re.sub(pattern, '', query).strip()
    
    # Separate file paths and URLs
    file_paths = []
    urls = []
    
    for match in matches:
        # Check if it's a URL (has domain-like structure)
        if match.startswith(('http://', 'https://')) or ('.' in match and '/' in match and not ':' in match):
            urls.append(match)
        else:
            # Check if there's a line range specification
            if ':' in match:
                parts = match.split(':', 1)
                file_path = parts[0]
                line_range = parts[1]
                
                # Parse the line range
                start_line = None
                end_line = None
                
                if '-' in line_range:
                    range_parts = line_range.split('-', 1)
                    
                    # Handle start line
                    if range_parts[0].strip():
                        try:
                            start_line = int(range_parts[0].strip())
                        except ValueError:
                            print(f"Warning: Invalid start line number in '{match}', using default")
                    
                    # Handle end line
                    if len(range_parts) > 1 and range_parts[1].strip():
                        try:
                            end_line = int(range_parts[1].strip())
                        except ValueError:
                            print(f"Warning: Invalid end line number in '{match}', using default")
                else:
                    # Single line number
                    try:
                        start_line = int(line_range.strip())
                        end_line = start_line + 1  # Read just this one line
                    except ValueError:
                        print(f"Warning: Invalid line number in '{match}', using default")
                
                file_paths.append((file_path, start_line, end_line))
            else:
                # No line range, just a file path
                file_paths.append((match, None, None))
    
    return clean_query, file_paths, urls


def is_search_query(query):
    """Check if the query is a search request."""
    return query.lower().startswith(("search:", "search "))


def is_edit_query(query):
    """Check if the query is a file edit request."""
    return query.lower().startswith(("edit:", "edit "))


def is_run_query(query):
    """Check if the query is a command execution request."""
    return query.lower().startswith(("run:", "run "))


def is_model_query(query):
    """Check if the query is a model change request."""
    return query.lower().startswith(("model:", "model ", "use model:", "use model "))


def extract_search_query(query):
    """Extract the actual search query from the input."""
    if query.lower().startswith("search:"):
        return query[7:].strip()
    elif query.lower().startswith("search "):
        return query[7:].strip()
    return query


def extract_edit_query(query):
    """Extract the edit instruction from an edit query."""
    if query.lower().startswith("edit:"):
        return query[5:].strip()
    elif query.lower().startswith("edit "):
        return query[5:].strip()
    return query


def extract_run_query(query):
    """Extract the command from a run query."""
    if query.lower().startswith("run:"):
        return query[4:].strip()
    elif query.lower().startswith("run "):
        return query[4:].strip()
    return query


def extract_model_query(query):
    """Extract the model name from a model query."""
    if query.lower().startswith("model:"):
        return query[6:].strip()
    elif query.lower().startswith("model "):
        return query[6:].strip()
    elif query.lower().startswith("use model:"):
        return query[10:].strip()
    elif query.lower().startswith("use model "):
        return query[10:].strip()
    return query


def extract_specific_command(query):
    """Extract a specific command from a query."""
    # Look for commands in single quotes
    match = re.search(r"'([^']*(?:''[^']*)*)'", query)
    if match:
        return match.group(1)
    
    # If no quoted command found, return None
    return None


def get_file_list():
    """Get a list of files in the current directory."""
    try:
        files = []
        for root, dirs, filenames in os.walk('.'):
            for filename in filenames:
                # Skip hidden files and directories
                if filename.startswith('.') or any(part.startswith('.') for part in root.split(os.sep)):
                    continue
                files.append(os.path.join(root, filename))
        return files
    except Exception as e:
        print(f"Error getting file list: {e}")
        return []


def get_ollama_response(history, model=None):
    """Get a response from the Ollama API."""
    # Use the specified model or the current model
    model_to_use = model or CURRENT_MODEL
    
    try:
        # Prepare the request payload
        payload = {
            "model": model_to_use,
            "messages": history,
            "stream": False
        }
        
        # Send the request to Ollama
        response = requests.post(OLLAMA_API_URL, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            return response.json().get("message", {}).get("content", "")
        else:
            error_msg = f"Error: Received status code {response.status_code} from Ollama API"
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
            return error_msg
    except Exception as e:
        error_msg = f"Error communicating with Ollama: {e}"
        print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
        return error_msg


def extract_modified_content(response, file_path):
    """Extract the modified content from the LLM's response."""
    # First, clean up the raw response - remove any markdown formatting (```), code block indicators, etc.
    cleaned_response = response.strip()
    
    # Check for responses indicating no changes were made
    no_changes_phrases = [
        "I did not make any changes",
        "I have not made any changes",
        "No changes were made",
        "No changes are needed",
        "I analyzed",
        "but did not make any changes"
    ]
    
    if any(phrase in cleaned_response.lower() for phrase in no_changes_phrases):
        print(f"{Fore.YELLOW}Warning: The LLM indicated it did not make any changes, which may be incorrect.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}This could be because it misunderstood the request or didn't follow instructions.{Style.RESET_ALL}")
        show_raw = input(f"{Fore.YELLOW}Do you want to see the raw response? (y/n): {Style.RESET_ALL}").lower()
        
        if show_raw in ('y', 'yes'):
            print("\nRaw response:")
            print(cleaned_response)
            return None
        else:
            return None
    
    # Check for code blocks with triple backticks - this is a common format for code in markdown
    code_blocks = []
    if "```" in cleaned_response:
        # Split by code block markers
        parts = cleaned_response.split("```")
        
        # If we have an odd number of parts, we have complete code blocks
        if len(parts) > 1:
            # Extract code blocks (every even-indexed part after the first)
            for i in range(1, len(parts), 2):
                if i < len(parts):
                    # Use lstrip() to only remove leading whitespace, not trailing
                    code_block = parts[i].lstrip()
                    # Remove language identifier if present
                    if code_block and "\n" in code_block:
                        first_line = code_block.split("\n")[0].strip()
                        # Check if first line looks like a language identifier (no spaces, no special chars)
                        if first_line and not any(c in first_line for c in "(){};:,./\\\"'=+-*&^%$#@!~`|<>?"):
                            # Use lstrip() to only remove leading whitespace, not trailing
                            code_block = code_block[code_block.find("\n")+1:].lstrip()
                    code_blocks.append(code_block)
    
    # If we found code blocks, use the last one (most likely the final version)
    if code_blocks:
        return clean_explanatory_text(code_blocks[-1])
    
    # If no code blocks found, proceed with the existing logic
    # If it starts and ends with code blocks, remove them
    if cleaned_response.startswith("```") and "```" in cleaned_response[3:]:
        # Find the first line break after the opening ```
        first_line_break = cleaned_response.find("\n", 3)
        if first_line_break != -1:
            # Skip the language identifier line
            cleaned_response = cleaned_response[first_line_break + 1:]
        
        # Find and remove the closing code block
        last_code_block = cleaned_response.rfind("```")
        if last_code_block != -1:
            cleaned_response = cleaned_response[:last_code_block].strip()
    
    # Fix indentation issues - check if there's consistent indentation
    lines = cleaned_response.split('\n')
    if len(lines) > 5:  # Only do this for responses with sufficient lines
        # Count leading spaces for non-empty lines
        indents = []
        for line in lines:
            if line.strip():  # Skip empty lines
                spaces = len(line) - len(line.lstrip())
                indents.append(spaces)
        
        # Find most common indent
        if indents:
            from collections import Counter
            most_common_indent, count = Counter(indents).most_common(1)[0]
            
            # If most lines have the same non-zero indent, remove it
            if most_common_indent > 0 and count > len(lines) * 0.5:  # If >50% of lines have this indent
                print(f"Note: Removing {most_common_indent} spaces of indentation from response")
                cleaned_lines = []
                for line in lines:
                    if line.startswith(' ' * most_common_indent):
                        cleaned_lines.append(line[most_common_indent:])
                    else:
                        cleaned_lines.append(line)
                cleaned_response = '\n'.join(cleaned_lines)
    
    # Since our prompt explicitly tells the LLM not to include markers like "Modified file:",
    # we should primarily treat the entire response as the file content
    file_content = cleaned_response
    
    # However, we'll still check for common patterns as a fallback
    patterns = [
        f"Modified {file_path}:",
        f"modified {file_path}:",
        f"Updated {file_path}:",
        f"updated {file_path}:",
        f"Modified content of {file_path}:",
        f"Content of {file_path}:",
        f"File content for {file_path}:",
    ]
    
    for pattern in patterns:
        if pattern in cleaned_response:
            # Split at the pattern and take what follows
            content = cleaned_response.split(pattern, 1)[1].strip()
            
            # Look for end markers like "Explanation:" that might signal the end of the content
            end_markers = [
                "\nExplanation:",
                "\nChanges made:",
                "\nHere's what changed:",
                "\nReasoning:",
                "\nSummary of changes:"
            ]
            
            for marker in end_markers:
                if marker in content:
                    content = content.split(marker, 1)[0].strip()
            
            file_content = content
            break
    
    # Clean up any explanatory text
    file_content = clean_explanatory_text(file_content)
    
    # Only show the warning if the content is very short or looks like an explanation rather than code
    if len(file_content.strip()) < 10 or file_content.lower().startswith(("i ", "i've ", "here's why", "the reason")):
        print(f"{Fore.YELLOW}Warning: Could not clearly identify file content in the LLM's response.{Style.RESET_ALL}")
        show_raw = input(f"{Fore.YELLOW}Do you want to see the raw response to manually extract content? (y/n): {Style.RESET_ALL}").lower()
        
        if show_raw in ('y', 'yes'):
            print("\nRaw response:")
            print(cleaned_response)
            
            # Ask if they want to use this content
            use_raw = input(f"{Fore.YELLOW}Do you want to use this raw response as the file content? (y/n): {Style.RESET_ALL}").lower()
            if use_raw in ('y', 'yes'):
                file_content = cleaned_response
            else:
                return None
    
    return file_content


def clean_explanatory_text(content):
    """Clean explanatory text from the content."""
    if not content:
        return content
        
    # Check for explanatory text at the beginning
    explanation_starters = [
        "Here's the modified file:",
        "Here's the updated file:",
        "Here's the edited file:",
        "I've made the following changes:",
        "I've updated the file as requested:",
        "The modified file content is:",
        "Suggested command:",
        "Command:",
        "I executed the command",
    ]
    
    for starter in explanation_starters:
        if content.startswith(starter):
            content = content[len(starter):].strip()
            break
    
    # Remove thinking blocks
    content = process_thinking_blocks(content)
    
    return content


def process_thinking_blocks(content):
    """Process thinking blocks in the content.
    
    Removes or truncates thinking blocks based on user preferences.
    """
    global SHOW_THINKING, MAX_THINKING_LENGTH
    
    if not content:
        return content
    
    # Check if there are thinking blocks
    think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
    
    # First, check if we have any thinking blocks
    if '<think>' not in content:
        return content
    
    # If thinking is disabled (default), simply remove all thinking blocks
    if not SHOW_THINKING:
        # Use regex to remove all thinking blocks
        return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
    
    # If thinking is enabled but needs truncation
    result = content
    matches = list(think_pattern.finditer(content))
    
    # Process each thinking block
    for match in reversed(matches):  # Process in reverse to maintain indices
        thinking_content = match.group(1)
        start, end = match.span()
        
        # Truncate if too long
        if len(thinking_content) > MAX_THINKING_LENGTH:
            truncated = thinking_content[:MAX_THINKING_LENGTH] + f"\n... [Thinking truncated, {len(thinking_content) - MAX_THINKING_LENGTH} more characters] ..."
            result = result[:start] + f"<thinking>\n{truncated}\n</thinking>" + result[end:]
    
    return result


def toggle_thinking_display():
    """Toggle whether to show thinking blocks."""
    global SHOW_THINKING
    SHOW_THINKING = not SHOW_THINKING
    status = "ON" if SHOW_THINKING else "OFF"
    print(f"{Fore.CYAN}Thinking display is now {status}{Style.RESET_ALL}")


def set_thinking_max_length(length):
    """Set the maximum length for displayed thinking blocks."""
    global MAX_THINKING_LENGTH
    try:
        length = int(length)
        if length < 100:
            print(f"{Fore.YELLOW}Warning: Setting thinking length too low may not be useful. Using minimum of 100.{Style.RESET_ALL}")
            length = 100
        MAX_THINKING_LENGTH = length
        print(f"{Fore.CYAN}Maximum thinking length set to {MAX_THINKING_LENGTH} characters{Style.RESET_ALL}")
    except ValueError:
        print(f"{Fore.RED}Error: Please provide a valid number for thinking length{Style.RESET_ALL}")


def extract_suggested_command(response):
    """Extract the suggested command from the LLM's response."""
    if not response:
        return None
    
    try:
        # First, process any thinking blocks
        cleaned_response = process_thinking_blocks(response)
        
        # Look for code blocks with triple backticks
        code_block_pattern = re.compile(r'```(?:bash|shell|cmd|powershell|sh)?\s*(.*?)```', re.DOTALL)
        code_blocks = code_block_pattern.findall(cleaned_response)
        
        if code_blocks:
            # Use the first code block
            command = code_blocks[0].strip()
            # If the command spans multiple lines, use only the first line
            if '\n' in command:
                command = command.split('\n')[0].strip()
            return command
        
        # Look for lines that start with common command prefixes
        lines = cleaned_response.split('\n')
        for line in lines:
            line = line.strip()
            
            # Check for lines that look like commands
            if line.startswith(('python ', 'python3 ', 'node ', 'npm ', 'git ', 'ls ', 'dir ', 'cd ')):
                return line
            
            # Check for lines that are explicitly labeled as commands
            command_prefixes = [
                "Command: ", 
                "Suggested command: ",
                "Run: ",
                "Execute: ",
                "Try: ",
                "Use: "
            ]
            
            for prefix in command_prefixes:
                if line.startswith(prefix):
                    return line[len(prefix):].strip()
        
        # Look for text between quotes that looks like a command
        quote_pattern = re.compile(r'[\'"`]((?:python|python3|node|npm|git|ls|dir|cd|grep|find|cat|type|pip|npm|yarn|dotnet|java|javac|gcc|g\+\+|make|cmake|mvn|gradle|cargo|rustc|go|ruby|perl|php|bash|sh|pwsh|powershell|cmd|echo|test|pytest|jest|mocha).*?)[\'"`]')
        quote_matches = quote_pattern.findall(cleaned_response)
        
        if quote_matches:
            return quote_matches[0]
        
        # If no command pattern is found, return the first non-empty line
        for line in lines:
            line = line.strip()
            if line:
                return line
        
        return None
    except Exception as e:
        print(f"{Fore.RED}Error extracting command: {e}{Style.RESET_ALL}")
        return None


def main():
    """Main function to run the coding assistant."""
    print(f"{Fore.CYAN}🤖 Local LLM Coding Assistant 🤖{Style.RESET_ALL}")
    print(f"{Fore.CYAN}================================{Style.RESET_ALL}")
    print("Enter your coding questions and include file paths in square brackets.")
    print("Example: How can I improve this code? [main.py]")
    print()
    print("For web searches, prefix with 'search:' or 'search ' - Example: search: Python requests library")
    print("For file editing, prefix with 'edit:' or 'edit ' - Example: edit: [main.py] to fix the function")
    print("For running commands, prefix with 'run:' or 'run ' - Example: run: the tests or run: 'python test.py'")
    print("For changing models, prefix with 'model:' or 'model ' - Example: model: llama3 or model: codellama")
    print("Include URLs in brackets - Example: How to use this API? [https://api.example.com/docs]")
    print()
    print("Special commands:")
    print("  'thinking:on' or 'thinking:off' - Toggle display of AI thinking blocks")
    print("  'thinking:length N' - Set maximum length of thinking blocks (N characters)")
    print("  'exit' - Quit the assistant")
    print()
    
    # Check Ollama connection
    if not check_ollama_connection():
        print("Exiting due to connection issues with Ollama.")
        sys.exit(1)
    
    # Initialize conversation history
    conversation_history = []
    
    # Display current model
    print(f"Current model: {CURRENT_MODEL}")
    print(f"Thinking display: {'ON' if SHOW_THINKING else 'OFF'}")
    print(f"Maximum thinking length: {MAX_THINKING_LENGTH} characters")
    print()
    
    while True:
        # Get user input
        user_input = input(f"\n{Fore.GREEN}> {Style.RESET_ALL}")
        
        # Check for exit command
        if user_input.lower() in ['exit', 'quit']:
            print("Goodbye! 👋")
            break
            
        # Check for thinking display commands
        if user_input.lower() in ['thinking:on', 'thinking on']:
            toggle_thinking_display()
            continue
        elif user_input.lower() in ['thinking:off', 'thinking off']:
            toggle_thinking_display()
            continue
        elif user_input.lower().startswith(('thinking:length ', 'thinking length ')):
            parts = user_input.split()
            if len(parts) >= 2:
                try:
                    length = int(parts[-1])
                    set_thinking_max_length(length)
                except ValueError:
                    print(f"{Fore.YELLOW}Invalid length value. Please provide a number.{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Usage: thinking:length NUMBER{Style.RESET_ALL}")
            continue
        
        # Check query type
        search_mode = is_search_query(user_input)
        edit_mode = is_edit_query(user_input)
        run_mode = is_run_query(user_input)
        model_mode = is_model_query(user_input)
        
        # Handle different query types
        if search_mode:
            handle_search_query(user_input, conversation_history)
        elif edit_mode:
            handle_edit_query(user_input, conversation_history)
        elif run_mode:
            handle_run_query(user_input, conversation_history)
        elif model_mode:
            handle_model_query(user_input, conversation_history)
        else:
            handle_regular_query(user_input, conversation_history)


def handle_search_query(user_input, conversation_history):
    """Handle web search queries."""
    # Extract the search query
    search_query = extract_search_query(user_input)
    
    print(f"{Fore.CYAN}Searching the web for: {search_query}{Style.RESET_ALL}")
    
    # Perform the search
    search_results = duckduckgo_search(search_query)
    
    if not search_results:
        print(f"{Fore.YELLOW}No search results found. Proceeding with just the query.{Style.RESET_ALL}")
        search_content = ""
    else:
        # Format search results for the prompt
        search_content = "\nSearch Results:\n"
        for i, result in enumerate(search_results, 1):
            search_content += f"{i}. {result['title']}\n"
            search_content += f"   URL: {result['url']}\n"
            search_content += f"   Snippet: {result['snippet']}\n\n"
    
    # Construct user message
    user_message = f"Web Search Query: {search_query}"
    if search_content:
        user_message += f"\n{search_content}"
    
    # Add the user message to the conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    # Print "Thinking..." to indicate processing
    print(f"\n{Fore.YELLOW}Thinking...{Style.RESET_ALL}\n")
    
    try:
        # Get response from Ollama
        assistant_response = get_ollama_response(conversation_history)
        
        # Process thinking blocks in the response
        processed_response = process_thinking_blocks(assistant_response)
        
        # Display the response
        print(f"{Fore.CYAN}🤖 Assistant:{Style.RESET_ALL}\n{processed_response}")
        
        # Add the assistant's response to the conversation history
        conversation_history.append({"role": "assistant", "content": assistant_response})
    except Exception as e:
        print(f"{Fore.RED}Error processing response: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}This might be due to a very large response or thinking block.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Try using a more specific query or setting a larger MAX_THINKING_LENGTH.{Style.RESET_ALL}")
        
        # Add a placeholder response to the conversation history
        conversation_history.append({
            "role": "assistant", 
            "content": "I encountered an error while processing the response. Please try a more specific query."
        })


def handle_edit_query(user_input, conversation_history):
    """Handle file editing queries."""
    # Extract the edit query
    edit_query = extract_edit_query(user_input)
    
    # Get file paths from the query
    clean_query, file_items, _ = extract_file_paths_and_urls(edit_query)
    
    if not file_items:
        print(f"{Fore.YELLOW}No file paths found in the query. Please include file paths in square brackets.{Style.RESET_ALL}")
        return
    
    # Read file contents
    files_content_section = "\nFiles to Edit:\n"
    for file_item in file_items:
        # Unpack the file path and line range
        if isinstance(file_item, tuple):
            file_path, start_line, end_line = file_item
        else:
            # For backward compatibility
            file_path, start_line, end_line = file_item, None, None
            
        content = read_file_content(file_path, start_line, end_line)
        if content:
            # Include line range info in the file header if specified
            if start_line is not None or end_line is not None:
                line_info = f" (lines {start_line or '1'}-{end_line or 'end'})"
                files_content_section += f"File: {file_path}{line_info}\nContent:\n{content}\n\n"
            else:
                files_content_section += f"File: {file_path}\nContent:\n{content}\n\n"
    
    # Construct user message
    user_message = f"Edit Request: {clean_query}"
    user_message += files_content_section
    
    # Add the user message to the conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    # Print "Thinking..." to indicate processing
    print(f"{Fore.CYAN}Thinking...{Style.RESET_ALL}")
    
    # Get the response from Ollama
    response = get_ollama_response(conversation_history)
    
    # Process and display the response
    if response:
        # Process thinking blocks
        processed_response = process_thinking_blocks(response)
        
        # Add the assistant's response to the conversation history
        conversation_history.append({"role": "assistant", "content": response})
        
        # Print the processed response
        print(f"{Fore.GREEN}{processed_response}{Style.RESET_ALL}")
        
        # Extract and apply modifications
        for file_item in file_items:
            # Get just the file path from the item
            if isinstance(file_item, tuple):
                file_path = file_item[0]
            else:
                file_path = file_item
                
            modified_content = extract_modified_content(response, file_path)
            if modified_content:
                # Confirm with the user before writing changes
                print(f"\n{Fore.YELLOW}Proposed changes to {file_path}:{Style.RESET_ALL}")
                
                # Get the original content for comparison
                original_content = read_file_content(file_path, None, None)  # Always read the entire file for editing
                
                if original_content and original_content != modified_content:
                    # Generate and display a colored diff
                    diff = generate_colored_diff(original_content, modified_content, file_path)
                    print(diff)
                    
                    # Ask for confirmation
                    confirm = input(f"{Fore.YELLOW}Apply these changes? (y/n): {Style.RESET_ALL}").lower()
                    if confirm == 'y':
                        write_file_content(file_path, modified_content)
                        print(f"{Fore.GREEN}Changes applied to {file_path}{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Changes to {file_path} discarded.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}No changes detected for {file_path}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Failed to get a response from the model.{Style.RESET_ALL}")


def handle_run_query(user_input, conversation_history):
    """Handle command execution queries."""
    # Extract the run query
    run_query = extract_run_query(user_input)
    
    # Construct user message
    user_message = f"Command Request: {run_query}\n"
    user_message += "Please suggest a command to run based on this request. "
    user_message += "Format your response with the command in a code block using triple backticks."
    
    # Add the user message to the conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    # Print "Thinking..." to indicate processing
    print(f"\n{Fore.YELLOW}Thinking about what command to run...{Style.RESET_ALL}\n")
    
    try:
        # Get response from Ollama
        assistant_response = get_ollama_response(conversation_history)
        
        # Process thinking blocks in the response
        processed_response = process_thinking_blocks(assistant_response)
        
        # Display the response
        print(f"{Fore.CYAN}🤖 Assistant:{Style.RESET_ALL}\n{processed_response}")
        
        # Add the assistant's response to the conversation history
        conversation_history.append({"role": "assistant", "content": assistant_response})
        
        # Extract the suggested command
        suggested_command = extract_suggested_command(assistant_response)
        
        if not suggested_command:
            print(f"{Fore.YELLOW}Could not extract a command from the response.{Style.RESET_ALL}")
            return
        
        # Check if the command is safe
        if not is_safe_command(suggested_command):
            print(f"{Fore.RED}Warning: The suggested command may be unsafe: {suggested_command}{Style.RESET_ALL}")
            print(f"{Fore.RED}This command contains potentially dangerous operations.{Style.RESET_ALL}")
            confirm = input(f"{Fore.YELLOW}Are you sure you want to run this command? (y/n): {Style.RESET_ALL}").lower()
            if confirm not in ('y', 'yes'):
                print(f"{Fore.YELLOW}Command execution cancelled.{Style.RESET_ALL}")
                return
        
        # Ask for confirmation
        print(f"\n{Fore.CYAN}Suggested command:{Style.RESET_ALL}")
        print(f"{Fore.GREEN}{suggested_command}{Style.RESET_ALL}")
        
        confirm = input(f"\n{Fore.YELLOW}Run this command? (y/n): {Style.RESET_ALL}").lower()
        
        if confirm in ('y', 'yes'):
            # Execute the command
            print(f"{Fore.CYAN}Executing command...{Style.RESET_ALL}")
            output = execute_command(suggested_command)
            
            # Display the output
            print(f"{Fore.CYAN}Command output:{Style.RESET_ALL}")
            print(output)
            
            # Add the command execution to the conversation history
            conversation_history.append({
                "role": "system", 
                "content": f"The command '{suggested_command}' was executed with the following output:\n{output}"
            })
        else:
            print(f"{Fore.YELLOW}Command execution cancelled.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error processing response: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}This might be due to a very large response or thinking block.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Try using a more specific query or setting a larger MAX_THINKING_LENGTH.{Style.RESET_ALL}")
        
        # Add a placeholder response to the conversation history
        conversation_history.append({
            "role": "assistant", 
            "content": "I encountered an error while processing the response. Please try a more specific query."
        })


def handle_model_query(user_input, conversation_history):
    """Handle model switching queries."""
    global CURRENT_MODEL
    
    # Extract the model name
    model_name = extract_model_query(user_input)
    
    if not model_name:
        print(f"{Fore.YELLOW}Could not extract a model name from the query.{Style.RESET_ALL}")
        return
    
    try:
        # Check if the model is available
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                available_models = [model.get("name") for model in response.json().get("models", [])]
                
                if model_name not in available_models:
                    print(f"{Fore.YELLOW}Warning: Model '{model_name}' not found in available models.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Available models: {', '.join(available_models)}{Style.RESET_ALL}")
                    
                    # Ask for confirmation
                    confirm = input(f"{Fore.YELLOW}Do you still want to try using this model? (y/n): {Style.RESET_ALL}").lower()
                    if confirm not in ('y', 'yes'):
                        print(f"{Fore.YELLOW}Model change cancelled.{Style.RESET_ALL}")
                        return
            else:
                print(f"{Fore.YELLOW}Warning: Could not verify available models. HTTP {response.status_code}{Style.RESET_ALL}")
                
                # Ask for confirmation
                confirm = input(f"{Fore.YELLOW}Do you want to try using model '{model_name}'? (y/n): {Style.RESET_ALL}").lower()
                if confirm not in ('y', 'yes'):
                    print(f"{Fore.YELLOW}Model change cancelled.{Style.RESET_ALL}")
                    return
        except requests.exceptions.RequestException as e:
            print(f"{Fore.YELLOW}Warning: Could not connect to Ollama to verify available models: {e}{Style.RESET_ALL}")
            
            # Ask for confirmation
            confirm = input(f"{Fore.YELLOW}Do you want to try using model '{model_name}'? (y/n): {Style.RESET_ALL}").lower()
            if confirm not in ('y', 'yes'):
                print(f"{Fore.YELLOW}Model change cancelled.{Style.RESET_ALL}")
                return
        
        # Change the model
        model = model_name.strip()
        
        # Ask for confirmation
        confirm = input(f"{Fore.YELLOW}Change model from {CURRENT_MODEL} to {model}? (y/n): {Style.RESET_ALL}").lower()
        
        if confirm in ('y', 'yes'):
            print(f"{Fore.CYAN}Changing model from {CURRENT_MODEL} to: {model}{Style.RESET_ALL}")
            CURRENT_MODEL = model
            
            # Add the model change to conversation history
            conversation_history.append({
                "role": "system", 
                "content": f"The model has been changed to {model}."
            })
        else:
            print(f"{Fore.YELLOW}Model change canceled. Still using: {CURRENT_MODEL}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error processing model change: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Model change failed. Still using: {CURRENT_MODEL}{Style.RESET_ALL}")


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
        for file_item in file_paths:
            # Unpack the file path and line range
            if isinstance(file_item, tuple):
                file_path, start_line, end_line = file_item
            else:
                # For backward compatibility
                file_path, start_line, end_line = file_item, None, None
                
            content = read_file_content(file_path, start_line, end_line)
            if content:
                # Include line range info in the file header if specified
                if start_line is not None or end_line is not None:
                    line_info = f" (lines {start_line or '1'}-{end_line or 'end'})"
                    files_content_section += f"File: {file_path}{line_info}\nContent:\n{content}\n\n"
                else:
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
    print(f"{Fore.CYAN}Thinking...{Style.RESET_ALL}")
    
    # Get the response from Ollama
    response = get_ollama_response(conversation_history)
    
    # Process and display the response
    if response:
        # Process thinking blocks
        processed_response = process_thinking_blocks(response)
        
        # Add the assistant's response to the conversation history
        conversation_history.append({"role": "assistant", "content": response})
        
        # Print the processed response
        print(f"{Fore.GREEN}{processed_response}{Style.RESET_ALL}")
    else:
        print(f"{Fore.RED}Failed to get a response from the model.{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
        sys.exit(0) 