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
- Create new empty files
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
  python code_assistant.py "Create: [newfile.py]"
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
import chardet  # Import chardet at the module level
from pathlib import Path
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
DEFAULT_TIMEOUT = 500  # Default timeout for LLM operations in seconds
WORKING_DIRECTORY = None  # Working directory for file operations

# Command execution safety
SAFE_COMMAND_PREFIXES = ["python", "python3", "node", "npm", "git", "ls", "dir", "cd", "type", "cat", "make", "dotnet", "gradle", "mvn", "cargo", "rustc", "go", "test", "echo"]
DANGEROUS_COMMANDS = ["rm", "del", "sudo", "chmod", "chown", "mv", "cp", "rmdir", "rd", "format", "mkfs", "dd", ">", ">>"]


def check_ollama_connection():
    """Verify the Ollama server is running and accessible."""
    try:
        print("Checking Ollama connection...")
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        
        # This will raise an HTTPError for status codes 4XX/5XX
        response.raise_for_status()
            
        data = response.json()
        
        models = [model["name"] for model in data.get("models", [])]
        
        if models:
            print("Ollama connection successful. Available models:")
            print(f"Available models: {', '.join(models)}")
            for model in models:
                print(f"- {model}")
        else:
            print("\nOllama is running but no models are available.")
            print("\nTo use this tool, you need to pull a model first. Run this command:")
            print("\n    ollama pull <model_name>")
            print("\nRecommended starter models:")
            print("- llama3 (Meta's Llama 3 8B model)")
            print("- mistral (Mistral AI's 7B model)")
            print("- neural-chat (Intelligent Neural Labs 7B model)")
            print("\nSee https://ollama.com/library for more options.")
            
        print()
        return True
    except requests.exceptions.HTTPError as e:
        # Handle HTTP error responses with detailed information
        status_code = getattr(e.response, 'status_code', '?')
        reason = getattr(e.response, 'reason', 'Unknown reason')
        error_text = getattr(e.response, 'text', '')
        
        print(f"\nError connecting to Ollama: HTTP {status_code} {reason}")
        if error_text:
            print(f"Details: {error_text}")
            
        # Provide more specific guidance based on the status code
        if status_code == 404:
            print("\nThe Ollama API endpoint was not found. Please check your Ollama installation.")
        elif status_code >= 500:
            print("\nThe Ollama server encountered an internal error.")
            print("Try restarting the Ollama server with 'ollama serve' in a separate terminal.")
            
        print()
        return False
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        print("\nError: Cannot connect to Ollama. Please ensure Ollama is running.")
        print("If not installed, download from: https://ollama.com/download")
        print("After installation, run 'ollama serve' in a separate terminal.")
        print()
        return False
    except Exception as e:
        print(f"\nUnexpected error when checking Ollama connection: {e}")
        print()
        return False


def detect_file_encoding(file_path):
    """Detect the encoding of a file using a combination of BOM detection,
    pattern analysis, and chardet for robust encoding detection.
    
    Returns:
        tuple: (encoding, bom) where bom is True if the file has a BOM
    """
    # First check for BOM using binary mode
    try:
        with open(file_path, 'rb') as f:
            # Read more bytes for better pattern detection
            raw = f.read(32)  # Read first 32 bytes for more reliable detection
            
            # Empty file check
            if not raw:
                return 'utf-8', False
                
            # Check for BOM markers - BOM detection is the most reliable method
            if raw.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
                return 'utf-8-sig', True
            elif raw.startswith(b'\xff\xfe\x00\x00'):  # UTF-32 LE BOM
                return 'utf-32-le', True
            elif raw.startswith(b'\x00\x00\xfe\xff'):  # UTF-32 BE BOM
                return 'utf-32-be', True
            elif raw.startswith(b'\xff\xfe'):  # UTF-16 LE BOM
                return 'utf-16-le', True
            elif raw.startswith(b'\xfe\xff'):  # UTF-16 BE BOM
                return 'utf-16-be', True
            
            # No BOM found, use pattern detection for common encodings
            # The order of these checks is important - check more specific patterns first
            
            # Check for UTF-32 patterns (must be checked before UTF-16)
            if len(raw) >= 16:
                # UTF-32-LE pattern: every 4th byte is non-zero, others are zero
                # Common for ASCII text in UTF-32-LE
                utf32_le_pattern = True
                for i in range(0, min(16, len(raw)), 4):
                    if i+3 < len(raw):
                        # Check if bytes follow the pattern: X 0 0 0 (for ASCII in UTF-32-LE)
                        if not (raw[i] != 0 and raw[i+1] == 0 and raw[i+2] == 0 and raw[i+3] == 0):
                            utf32_le_pattern = False
                            break
                
                if utf32_le_pattern and len(raw) >= 8:
                    return 'utf-32-le', False
                
                # UTF-32-BE pattern: first byte of each 4-byte group is zero
                # Common for ASCII text in UTF-32-BE
                utf32_be_pattern = True
                for i in range(0, min(16, len(raw)), 4):
                    if i+3 < len(raw):
                        # Check if bytes follow the pattern: 0 0 0 X (for ASCII in UTF-32-BE)
                        if not (raw[i] == 0 and raw[i+1] == 0 and raw[i+2] == 0 and raw[i+3] != 0):
                            utf32_be_pattern = False
                            break
                
                if utf32_be_pattern and len(raw) >= 8:
                    return 'utf-32-be', False
            
            # Check for UTF-16 patterns - more strict checking to avoid false positives
            if len(raw) >= 8:
                # UTF-16-LE pattern: alternating non-zero and zero bytes for ASCII
                utf16_le_pattern = True
                zero_byte_count = 0
                
                # Check if pattern generally follows: X 0 X 0 X 0 (for ASCII in UTF-16-LE)
                for i in range(min(16, len(raw))):
                    if i % 2 == 1 and raw[i] == 0:
                        zero_byte_count += 1
                
                # Check if at least half of even-indexed bytes are non-zero
                # and most odd-indexed bytes are zero (for ASCII text)
                non_zero_odd = sum(1 for i in range(0, min(16, len(raw)), 2) if raw[i] != 0)
                if zero_byte_count >= 4 and non_zero_odd >= 3:
                    return 'utf-16-le', False
                
                # UTF-16-BE pattern: zero byte followed by non-zero byte for ASCII
                utf16_be_pattern = True
                zero_byte_count = 0
                
                # Check if pattern generally follows: 0 X 0 X 0 X (for ASCII in UTF-16-BE)
                for i in range(min(16, len(raw))):
                    if i % 2 == 0 and raw[i] == 0:
                        zero_byte_count += 1
                
                # Check if at least half of odd-indexed bytes are non-zero
                # and most even-indexed bytes are zero (for ASCII text)
                non_zero_even = sum(1 for i in range(1, min(16, len(raw)), 2) if raw[i] != 0)
                if zero_byte_count >= 4 and non_zero_even >= 3:
                    return 'utf-16-be', False
            
            # Rewind the file for chardet analysis
            f.seek(0)
            # Sample the first 4KB of the file for better detection
            raw_data = f.read(4096)
            
            # Use chardet for encoding detection when patterns aren't conclusive
            try:
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                confidence = result['confidence']
                
                if encoding:
                    if confidence < 0.7:
                        print(f"Warning: Low confidence ({confidence:.2f}) in detected encoding: {encoding}")
                    return encoding, False
            except Exception as e:
                print(f"Warning: Error using chardet: {e}")
                # Fall back to the legacy method
                return _legacy_detect_file_encoding(file_path)
                
    except Exception as e:
        print(f"Warning: Error detecting encoding: {e}")
    
    # Default to UTF-8 if all detection methods fail
    return 'utf-8', False


def _legacy_detect_file_encoding(file_path):
    """Legacy method to detect file encoding without chardet."""
    # Try to detect encoding with these common types
    encodings_to_try = ['utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
    
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
    try:
        # Ensure the file path is within the working directory if set
        if WORKING_DIRECTORY and not os.path.isabs(file_path):
            file_path = os.path.join(WORKING_DIRECTORY, file_path)
        elif WORKING_DIRECTORY and os.path.isabs(file_path):
            # Check if the absolute path is within the working directory
            if not os.path.abspath(file_path).startswith(WORKING_DIRECTORY):
                error_msg = f"Error: File '{file_path}' is outside the working directory. Access denied."
                print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
                return None
                
        # Check if file exists
        if not os.path.exists(file_path):
            error_msg = f"Error: File '{file_path}' not found."
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            
            # Try to provide helpful suggestions
            dir_path = os.path.dirname(file_path) or '.'
            if os.path.exists(dir_path):
                try:
                    similar_files = [f for f in os.listdir(dir_path) 
                                    if os.path.isfile(os.path.join(dir_path, f)) and 
                                    f.endswith(os.path.splitext(file_path)[1])]
                    if similar_files:
                        print(f"{Fore.YELLOW}Similar files in the directory:{Style.RESET_ALL}")
                        for f in similar_files[:5]:  # Show up to 5 similar files
                            print(f"{Fore.YELLOW}- {f}{Style.RESET_ALL}")
                        if len(similar_files) > 5:
                            print(f"{Fore.YELLOW}... and {len(similar_files) - 5} more{Style.RESET_ALL}")
                except Exception:
                    pass  # Ignore errors in the suggestion logic
            
            return None
            
        # Check if file is readable
        if not os.access(file_path, os.R_OK):
            error_msg = f"Error: File '{file_path}' is not readable. Check file permissions."
            print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
            return None
            
        # Check file size
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10 MB
            print(f"{Fore.YELLOW}Warning: File '{file_path}' is large ({file_size / 1024 / 1024:.2f} MB).{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Reading large files may cause performance issues.{Style.RESET_ALL}")
            
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
                    
                    # Validate line numbers
                    total_lines = len(lines)
                    
                    # Adjust for 1-indexed input to 0-indexed list
                    start_idx = max(0, (start_line or 1) - 1)
                    # If end_line is None, read to the end of the file
                    end_idx = min(total_lines, end_line) if end_line is not None else total_lines
                    
                    # Warn if line numbers are out of range
                    if start_line and start_line > total_lines:
                        print(f"{Fore.YELLOW}Warning: Start line {start_line} is beyond the end of the file ({total_lines} lines).{Style.RESET_ALL}")
                        start_idx = 0
                    if end_line and end_line > total_lines:
                        print(f"{Fore.YELLOW}Warning: End line {end_line} is beyond the end of the file ({total_lines} lines). Reading to the end.{Style.RESET_ALL}")
                    
                    # Extract the requested lines
                    selected_lines = lines[start_idx:end_idx]
                    content = ''.join(selected_lines)
                    
                    # Add a note about the line range
                    line_info = f"Lines {start_idx + 1}-{end_idx} of {total_lines} total lines"
                    content = f"--- {line_info} ---\n{content}"
                
            # Let the user know if we're using a non-standard encoding
            if encoding.lower() not in ['utf-8', 'utf-8-sig', 'ascii']:
                print(f"{Fore.CYAN}Note: File '{file_path}' was read with {encoding} encoding.{Style.RESET_ALL}")
                
            return content
                
        except UnicodeDecodeError as e:
            print(f"{Fore.RED}Error: Failed to decode file '{file_path}' with {encoding} encoding.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Error details: {str(e)}{Style.RESET_ALL}")
            
            # If all else fails, try binary mode as a last resort
            try:
                with open(file_path, 'rb') as file:
                    binary_content = file.read()
                    # Try to decode as latin-1 which can handle any byte value
                    print(f"{Fore.YELLOW}Using binary fallback with latin-1 encoding for '{file_path}'.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Some characters may not display correctly.{Style.RESET_ALL}")
                    return binary_content.decode('latin-1', errors='replace')
            except Exception as e2:
                error_type = type(e2).__name__
                print(f"{Fore.RED}Error reading file in binary mode: {error_type} - {str(e2)}{Style.RESET_ALL}")
                return None
                
        except Exception as e:
            error_type = type(e).__name__
            print(f"{Fore.RED}Error reading file '{file_path}': {error_type} - {str(e)}{Style.RESET_ALL}")
            
            # If all else fails, try binary mode as a last resort
            try:
                with open(file_path, 'rb') as file:
                    binary_content = file.read()
                    # Try to decode as latin-1 which can handle any byte value
                    print(f"{Fore.YELLOW}Using binary fallback with latin-1 encoding for '{file_path}'.{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}Some characters may not display correctly.{Style.RESET_ALL}")
                    return binary_content.decode('latin-1', errors='replace')
            except Exception as e2:
                error_type = type(e2).__name__
                print(f"{Fore.RED}Error reading file in binary mode: {error_type} - {str(e2)}{Style.RESET_ALL}")
                return None
    
    except Exception as e:
        error_type = type(e).__name__
        print(f"{Fore.RED}Unexpected error accessing file '{file_path}': {error_type} - {str(e)}{Style.RESET_ALL}")
        return None


def write_file_content(file_path, content, create_backup=True):
    """Write content to a file, preserving the original encoding."""
    try:
        # Ensure the file path is within the working directory if set
        if WORKING_DIRECTORY and not os.path.isabs(file_path):
            file_path = os.path.join(WORKING_DIRECTORY, file_path)
        elif WORKING_DIRECTORY and os.path.isabs(file_path):
            # Check if the absolute path is within the working directory
            if not os.path.abspath(file_path).startswith(WORKING_DIRECTORY):
                error_msg = f"Error: Cannot write to '{file_path}' as it is outside the working directory. Access denied."
                print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
                return False
        
        # Create parent directories if they don't exist
        parent_dir = os.path.dirname(file_path)
        if parent_dir and not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
            print(f"{Fore.GREEN}Created directory: {parent_dir}{Style.RESET_ALL}")
        
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
    """
    Check if a command is likely safe to execute using a whitelist approach.
    
    Returns:
        tuple: (is_safe, reason) where is_safe is a boolean and reason is a string or None
    """
    # Trim the command
    command = command.strip()
    
    # Check for command separators (;, &&, ||) which could chain dangerous commands
    for separator in [';', '&&', '||']:
        if separator in command:
            # Split by separator and check each command separately
            sep_commands = [cmd.strip() for cmd in command.split(separator)]
            for i, cmd in enumerate(sep_commands):
                is_safe, reason = is_safe_command(cmd)
                if not is_safe:
                    return False, f"Unsafe command in chain (part {i+1}): {reason}"
            return True, None
    
    # Check for pipe operators which could chain dangerous commands
    if '|' in command:
        # Split by pipe and check each command separately
        pipe_commands = [cmd.strip() for cmd in command.split('|')]
        for i, cmd in enumerate(pipe_commands):
            is_safe, reason = is_safe_command(cmd)
            if not is_safe:
                return False, f"Unsafe command in pipe (part {i+1}): {reason}"
        return True, None
    
    # Split the command to get the base command and arguments
    # This handles quoted arguments correctly
    try:
        import shlex
        parts = shlex.split(command)
    except Exception:
        return False, "Could not parse command safely"
    
    if not parts:
        return False, "Empty command"
    
    base_cmd = parts[0].lower()
    
    # Whitelist approach - only explicitly allowed commands are permitted
    ALLOWED_COMMANDS = {
        # Python commands with restrictions
        "python": lambda args: _check_python_args(args),
        "python3": lambda args: _check_python_args(args),
        
        # File listing and navigation (safe)
        "ls": lambda args: (True, None),
        "dir": lambda args: (True, None),
        "cd": lambda args: (True, None),
        "pwd": lambda args: (True, None),
        
        # File viewing and text processing (safe)
        "cat": lambda args: _check_file_args(args),
        "type": lambda args: _check_file_args(args),
        "more": lambda args: _check_file_args(args),
        "grep": lambda args: (True, None),
        "findstr": lambda args: (True, None),
        "find": lambda args: _check_find_args(args),
        "sort": lambda args: (True, None),
        "head": lambda args: (True, None),
        "tail": lambda args: (True, None),
        
        # Git commands with restrictions
        "git": lambda args: _check_git_args(args),
        
        # Package managers with restrictions
        "npm": lambda args: _check_npm_args(args),
        "pip": lambda args: _check_pip_args(args),
        
        # Build tools (generally safe)
        "make": lambda args: (True, None),
        "dotnet": lambda args: (True, None),
        "gradle": lambda args: (True, None),
        "mvn": lambda args: (True, None),
        "cargo": lambda args: (True, None),
        
        # Programming language tools (generally safe)
        "rustc": lambda args: (True, None),
        "go": lambda args: (True, None),
        
        # Testing and echo (safe)
        "test": lambda args: (True, None),
        "echo": lambda args: (True, None),
    }
    
    # Check if the base command is in our whitelist
    if base_cmd not in ALLOWED_COMMANDS:
        return False, f"Command '{base_cmd}' is not in the allowed list"
    
    # Apply the specific checker for this command
    args = parts[1:] if len(parts) > 1 else []
    is_safe, reason = ALLOWED_COMMANDS[base_cmd](args)
    
    return is_safe, reason


def _check_python_args(args):
    """Check if Python command arguments are safe."""
    if not args:
        return True, None
        
    # Check for dangerous flags
    dangerous_flags = ['-c', '--command']
    for flag in dangerous_flags:
        if flag in args:
            return False, f"Python with '{flag}' flag is not allowed for security reasons"
    
    # Check if the script file exists
    if args and not args[0].startswith('-'):
        script_path = args[0]
        # For testing purposes, we'll allow non-existent scripts if they don't contain suspicious patterns
        if '..' in script_path or script_path.startswith('/') or ':' in script_path:
            return False, f"Python script path '{script_path}' contains suspicious patterns"
        if os.path.exists(script_path):
            # If the file exists, we could do additional checks here
            # For example, scan the file content for dangerous imports
            pass
    
    return True, None


def _check_file_args(args):
    """Check if file-related command arguments are safe."""
    # Block any argument containing path traversal attempts
    for arg in args:
        if '..' in arg:
            return False, "Path traversal detected in arguments"
    return True, None


def _check_git_args(args):
    """Check if git command arguments are safe."""
    if not args:
        return True, None
        
    # Block potentially dangerous git commands
    dangerous_git_cmds = ['clean', 'reset', 'push', 'filter-branch']
    if args and args[0] in dangerous_git_cmds:
        return False, f"Git command '{args[0]}' requires manual review"
    
    return True, None


def _check_npm_args(args):
    """Check if npm command arguments are safe."""
    if not args:
        return True, None
        
    # Block potentially dangerous npm commands
    dangerous_npm_cmds = ['publish', 'unpublish', 'deprecate', 'access', 'adduser', 'login']
    if args and args[0] in dangerous_npm_cmds:
        return False, f"NPM command '{args[0]}' requires manual review"
    
    return True, None


def _check_pip_args(args):
    """Check if pip command arguments are safe."""
    if not args:
        return True, None
        
    # Block potentially dangerous pip commands
    dangerous_pip_cmds = ['uninstall']
    if args and args[0] in dangerous_pip_cmds:
        return False, f"Pip command '{args[0]}' requires manual review"
    
    return True, None


def _check_find_args(args):
    """Check if find command arguments are safe."""
    # Block any argument containing potentially dangerous options
    dangerous_options = ['-exec', '-delete']
    for arg in args:
        if arg in dangerous_options:
            return False, f"Find with '{arg}' option is not allowed for security reasons"
    return True, None


def execute_command(command):
    """Execute a command and return its output."""
    try:
        # Parse the command into arguments
        import shlex
        try:
            args = shlex.split(command)
        except Exception:
            # If parsing fails, fall back to shell=True but with extra caution
            return _execute_with_shell(command)
        
        if not args:
            return "Error: Empty command"
            
        # Execute without shell when possible (more secure)
        result = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            cwd=WORKING_DIRECTORY if WORKING_DIRECTORY else None
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


def _execute_with_shell(command):
    """Execute a command using shell=True as a fallback method."""
    try:
        # Run the command with shell=True (less secure, but handles complex commands)
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=WORKING_DIRECTORY if WORKING_DIRECTORY else None
        )
        
        # Prepare output
        output = "Note: Command executed with shell=True (less secure)\n"
        if result.stdout:
            output += f"Standard Output:\n{result.stdout}\n"
        if result.stderr:
            output += f"Standard Error:\n{result.stderr}\n"
        
        output += f"Exit Code: {result.returncode}"
        return output
    except Exception as e:
        return f"Error executing command with shell: {e}"


def fetch_url_content(url):
    """Fetch and extract text content from a URL."""
    try:
        # Add scheme if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            print(f"Added https:// prefix to URL: {url}")
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Fetching content from: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.Timeout:
            return f"Failed to fetch: Connection to {url} timed out after 10 seconds. The server might be slow or unavailable."
        except requests.exceptions.ConnectionError:
            return f"Failed to fetch: Could not establish a connection to {url}. Please check your internet connection or verify the URL is correct."
        except requests.exceptions.TooManyRedirects:
            return f"Failed to fetch: Too many redirects when accessing {url}. The URL might be in a redirect loop."
        
        if response.status_code == 200:
            # Try to determine content type
            content_type = response.headers.get('Content-Type', '').lower()
            print(f"Content type: {content_type}")
            
            # If it's HTML, parse with BeautifulSoup
            if 'text/html' in content_type:
                try:
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
                        print(f"Content truncated to {MAX_URL_CONTENT_LENGTH} characters")
                    
                    return text
                except Exception as e:
                    print(f"Error parsing HTML content: {e}")
                    # Fall back to raw text if HTML parsing fails
                    text = response.text
                    if len(text) > MAX_URL_CONTENT_LENGTH:
                        text = text[:MAX_URL_CONTENT_LENGTH] + "... [content truncated]"
                    return text
            else:
                # For non-HTML content, just return the raw text
                text = response.text
                if len(text) > MAX_URL_CONTENT_LENGTH:
                    text = text[:MAX_URL_CONTENT_LENGTH] + "... [content truncated]"
                    print(f"Content truncated to {MAX_URL_CONTENT_LENGTH} characters")
                return text
        elif response.status_code == 404:
            return f"Failed to fetch: The requested URL {url} was not found (404). Please check if the URL is correct."
        elif response.status_code == 403:
            return f"Failed to fetch: Access to {url} is forbidden (403). The website may be blocking automated access."
        elif response.status_code == 500:
            return f"Failed to fetch: The server at {url} encountered an internal error (500). Please try again later."
        elif response.status_code == 429:
            return f"Failed to fetch: Too many requests to {url} (429). The website is rate-limiting access."
        else:
            return f"Failed to fetch: {url}: HTTP status {response.status_code}"
    except requests.exceptions.RequestException as e:
        error_type = type(e).__name__
        return f"Failed to fetch: Request failed for {url}: {error_type} - {str(e)}"
    except Exception as e:
        error_type = type(e).__name__
        return f"Failed to fetch: Unexpected {error_type} when processing {url}: {str(e)}"


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
    # Updated pattern to handle nested brackets
    pattern = r'\[((?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*)\]'
    matches = re.findall(pattern, query)
    
    # Remove the bracketed content from the query
    clean_query = re.sub(pattern, '', query).strip()
    
    # Separate file paths and URLs
    file_paths = []
    urls = []
    
    for match in matches:
        # Skip empty matches
        if not match.strip():
            continue
            
        # Check if it's a URL - must start with http/https or have a valid domain structure
        if match.startswith(('http://', 'https://')) or (
            # Check for domain-like structure (e.g. example.com/path)
            # but exclude common file path patterns like ./path or ../path
            not match.startswith(('./', '../')) and
            '.' in match and 
            '/' in match and 
            not ':' in match and
            # Look for domain-like structure (letters/numbers followed by dot)
            re.search(r'^[a-zA-Z0-9][a-zA-Z0-9-]*\.[a-zA-Z]{2,}', match)
        ):
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
    """Check if the query is a search query."""
    return query.lower().startswith(("search:", "search "))


def is_edit_query(query):
    """Check if the query is an edit query."""
    return query.lower().startswith(("edit:", "edit "))


def is_run_query(query):
    """Check if the query is a run command query."""
    return query.lower().startswith(("run:", "run "))


def is_model_query(query):
    """Check if the query is a model query."""
    return query.lower().startswith(("model:", "model ", "use model:", "use model "))


def is_create_query(query):
    """Check if the query is a create query."""
    return query.lower().startswith(("create:", "create "))


def is_plan_query(query):
    """Check if the query is a plan query."""
    return query.lower().startswith(("plan:", "plan ", "vibecode:", "vibecode "))


def extract_create_query(query):
    """Extract the create query from the input."""
    if query.lower().startswith("create:"):
        return query[7:].strip()
    elif query.lower().startswith("create "):
        return query[7:].strip()
    return query


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
        model = query[6:].strip()
    elif query.lower().startswith("model "):
        model = query[6:].strip()
    elif query.lower().startswith("use model:"):
        model = query[10:].strip()
    elif query.lower().startswith("use model "):
        model = query[10:].strip()
    else:
        model = query
    
    # Strip quotes if present (both single and double quotes)
    if (model.startswith("'") and model.endswith("'")) or (model.startswith('"') and model.endswith('"')):
        model = model[1:-1].strip()
    
    return model


def extract_plan_query(query):
    """
    Extract the plan description from a query.
    
    Args:
        query (str): The user's query
        
    Returns:
        str: The plan description
    """
    # Remove the "plan:" prefix
    if query.lower().startswith("plan:"):
        return query[5:].strip()
    elif query.lower().startswith("plan "):
        return query[5:].strip()
    elif query.lower().startswith("vibecode:"):
        return query[9:].strip()
    elif query.lower().startswith("vibecode "):
        return query[9:].strip()
    else:
        return query.strip()


def extract_specific_command(query):
    """Extract a specific command from a query."""
    # Look for commands in single quotes
    match = re.search(r"'([^']*(?:''[^']*)*)'", query)
    if match:
        return match.group(1)
    
    # If no quoted command found, return None
    return None


def get_file_list():
    """Get a list of files in the working directory."""
    try:
        files = []
        search_dir = WORKING_DIRECTORY if WORKING_DIRECTORY else '.'
        
        for root, dirs, filenames in os.walk(search_dir):
            for filename in filenames:
                # Skip hidden files and directories
                if filename.startswith('.') or any(part.startswith('.') for part in root.split(os.sep)):
                    continue
                # Return paths relative to the working directory
                if WORKING_DIRECTORY:
                    rel_path = os.path.relpath(os.path.join(root, filename), WORKING_DIRECTORY)
                    files.append(rel_path)
                else:
                    files.append(os.path.join(root, filename))
        return files
    except Exception as e:
        print(f"{Fore.RED}Error listing files: {e}{Style.RESET_ALL}")
        return []


def set_timeout(timeout):
    """Set the timeout value for LLM operations.
    
    Args:
        timeout: New timeout value in seconds
        
    Returns:
        The updated timeout value
    """
    global DEFAULT_TIMEOUT
    try:
        timeout_value = int(timeout)
        if timeout_value <= 0:
            print(f"{Fore.YELLOW}Timeout must be a positive integer. Using current value of {DEFAULT_TIMEOUT}.{Style.RESET_ALL}")
            return DEFAULT_TIMEOUT
        DEFAULT_TIMEOUT = timeout_value
        print(f"{Fore.GREEN}Timeout set to {DEFAULT_TIMEOUT} seconds.{Style.RESET_ALL}")
        return DEFAULT_TIMEOUT
    except ValueError:
        print(f"{Fore.YELLOW}Invalid timeout value. Please provide a number.{Style.RESET_ALL}")
        return DEFAULT_TIMEOUT


def get_available_models():
    """
    Get a list of available models from the Ollama server.
    
    Returns:
        list: A list of available model names, or an empty list if none found or if an error occurs
    """
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        return [model["name"] for model in data.get("models", [])]
    except requests.exceptions.HTTPError as e:
        print(f"Error fetching available models: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"Connection error when fetching models: {e}")
        return []
    except (ValueError, KeyError) as e:
        print(f"Error parsing models response: {e}")
        return []


def _try_get_ollama_response(history, model, timeout=DEFAULT_TIMEOUT):
    """
    Helper function to make an Ollama API request.
    
    Args:
        history (list): The conversation history
        model (str): The model to use
        timeout (int): Request timeout in seconds
        
    Returns:
        str: The model's response or an error message
        
    Raises:
        Various requests exceptions if the request fails
    """
    options = {"max_tokens": 4000, "temperature": 0.7}  # Hardcoded values for these options
    payload = {
        "model": model,
        "messages": history,
        "options": options,
        "stream": False  # Explicitly set streaming to False
    }
    
    response = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=timeout
    )
    
    response.raise_for_status()
    
    if not response.text:
        raise ValueError("Empty response from Ollama")
    
    try:
        data = response.json()
        return data["message"]["content"]
    except (json.JSONDecodeError, KeyError):
        raise ValueError(f"Invalid JSON response: {response.text}")


def _sanitize_response_content(content):
    """Sanitize the response content to ensure thinking blocks are properly formed.
    
    This function handles cases where thinking blocks might be truncated or malformed
    in the response from the API.
    
    Args:
        content (str): The raw response content from Ollama API.
        
    Returns:
        str: Sanitized content with properly formed thinking blocks.
    """
    if not content:
        return content
        
    # Check for mismatched thinking tags
    think_open_count = content.count("<think>")
    think_close_count = content.count("</think>")
    
    # If we have unclosed thinking blocks (more opens than closes)
    if think_open_count > think_close_count:
        print(f"Warning: Detected {think_open_count - think_close_count} unclosed thinking block(s) in response")
        
        # Find the last position of an unclosed <think> tag
        last_think_pos = content.rfind("<think>")
        last_close_pos = content.rfind("</think>")
        
        if last_think_pos > last_close_pos:
            # We have an unclosed think tag at the end
            # Truncate the content at the last unclosed <think> tag to prevent leaking
            # This is safer than trying to add closing tags which might be incorrect
            content = content[:last_think_pos]
            print(f"Truncated response at unclosed thinking block")
    
    # Handle any standalone think tags that might cause issues
    # This happens if we have mismatched tags elsewhere in the content
    content = re.sub(r'<think>[^<]*$', '', content)  # Remove trailing incomplete thinking blocks
    
    return content


def get_ollama_response(history, model=None, timeout=None, allow_fallback=True):
    """
    Get a response from the Ollama API.
    
    Args:
        history (list): The conversation history
        model (str): The model to use, defaults to CURRENT_MODEL if None
        timeout (int): Request timeout in seconds, defaults to DEFAULT_TIMEOUT if None
        allow_fallback (bool): Whether to try other available models if the specified model fails
        
    Returns:
        str: The model's response or an error message
    """
    # Use defaults if not specified
    model_to_use = model if model is not None else CURRENT_MODEL
    timeout_to_use = timeout if timeout is not None else DEFAULT_TIMEOUT
    
    try:
        response = _try_get_ollama_response(history, model_to_use, timeout_to_use)
        return _sanitize_response_content(response)
    except requests.exceptions.Timeout:
        error_message = f"Request to Ollama API timed out after {timeout_to_use} seconds. The model might be taking too long to respond."
        print(f"{Fore.RED}{error_message}{Style.RESET_ALL}")
        return f"Error: Request to Ollama timed out after {timeout_to_use} seconds. Consider increasing the timeout or using a smaller model."
    except requests.exceptions.ConnectionError:
        # Add a printed message suggesting to check if Ollama is still running
        print("Connection error: Cannot connect to Ollama. Please check if Ollama is still running.")
        return (
            "Connection error: Cannot connect to Ollama. Please ensure Ollama is still running.\n"
            "If not installed, download from: https://ollama.com/download\n"
            "After installation, run 'ollama serve' in a separate terminal."
        )
    except requests.exceptions.HTTPError as e:
        # Check if error is due to model not found (404)
        if e.response.status_code == 404:
            # Always print the model not found message
            print(f"Model '{model_to_use}' not found.")
            
            if allow_fallback:
                available_models = get_available_models()
                
                if available_models:
                    fallback_model = available_models[0]
                    print(f"Falling back to available model: {fallback_model}")
                    
                    # Add system message to history about fallback
                    fallback_message = {
                        "role": "system", 
                        "content": f"Note: The requested model '{model_to_use}' was not available. Using '{fallback_model}' instead."
                    }
                    history.append(fallback_message)
                    
                    try:
                        return _try_get_ollama_response(history, fallback_model, timeout_to_use)
                    except Exception as fallback_err:
                        return f"Error: Failed to use fallback model '{fallback_model}': {fallback_err}"
                else:
                    print("\nNo models available for fallback. To use this tool, you need to pull a model:")
                    print("\n    ollama pull <model_name>")
                    print("\nRecommended starter models:")
                    print("- llama3 (Meta's Llama 3 8B model)")
                    print("- mistral (Mistral AI's 7B model)")
                    print("- neural-chat (Intelligent Neural Labs 7B model)")
                    print("\nSee https://ollama.com/library for more options.")
            
            # If no fallback or fallback not applicable, return the original error
            return f"Model '{model_to_use}' not found. Pull the model with 'ollama pull {model_to_use}' or use an available model."
        
        # Handle other HTTP errors
        status_code = getattr(e.response, 'status_code', '?')
        reason = getattr(e.response, 'reason', 'Unknown reason')
        error_text = getattr(e.response, 'text', '')
        
        # Special handling for 500 errors
        if status_code >= 500:
            print(f"The Ollama server encountered an internal error. You may need to restart the Ollama server.")
            return f"Error {status_code}: Internal server error. {error_text}"
            
        return f"Error {status_code} {reason}: {error_text}"
    except ValueError as e:
        if "Invalid JSON response" in str(e):
            return f"Failed to parse JSON response: {e}"
        return f"Error: {e}"
    except Exception as e:
        return f"Unexpected error: {e}"


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

     # Check for explanatory text at the end
    explanation_enders = [
        "This fixes the syntax error.",
        "This adds the missing",
        "This corrects the",
        "The code now has",
        "Now the code is syntactically correct.",
        "This completes the function.",
        "I've added the closing",
        "I've added the semicolon",
    ]
    
    for ender in explanation_enders:
        if content.endswith(ender):
            content = content[:content.rfind(ender)].strip()
            break
    
    
    # Remove thinking blocks
    content = process_thinking_blocks(content)
    
    return content


def process_thinking_blocks(content, chunk_size=10000):
    """Process thinking blocks in chunks to handle extremely large responses.
    
    Breaks down large responses into manageable chunks for regex processing,
    which helps prevent timeouts or excessive memory usage.
    
    Args:
        content (str): The raw response content from Ollama.
        chunk_size (int): Size of chunks to process at once.
        
    Returns:
        str: The processed content with thinking blocks handled.
    """
    global SHOW_THINKING, MAX_THINKING_LENGTH
    
    if not content:
        return content
        
    # Quick early return if no thinking blocks
    if '<think>' not in content:
        return content
        
    # For smaller content, use direct regex regardless of show/hide setting
    if len(content) <= chunk_size:
        if not SHOW_THINKING:
            return re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        else:
            return _process_thinking_blocks_simple(content, min(MAX_THINKING_LENGTH, 1000))
    
    # For larger content, always use chunking approach regardless of show/hide setting
    if not SHOW_THINKING:
        return _remove_thinking_blocks_chunked(content, chunk_size)
    else:
        return _process_thinking_blocks_chunked(content, min(MAX_THINKING_LENGTH, 1000), chunk_size)


def _remove_thinking_blocks_chunked(content, chunk_size):
    """Remove thinking blocks using a chunked approach for large content.
    
    Args:
        content (str): The content to process.
        chunk_size (int): Size of chunks to process.
        
    Returns:
        str: The content with all thinking blocks removed.
    """
    # Split at tag boundaries to ensure reliable processing
    parts = re.split(r'(<think>|</think>)', content)
    
    inside_thinking = False
    result = []
    
    for part in parts:
        if part == "<think>":
            inside_thinking = True
        elif part == "</think>":
            inside_thinking = False
        elif not inside_thinking:
            # Only keep content outside of thinking blocks
            result.append(part)
    
    return ''.join(result)


def _process_thinking_blocks_simple(content, max_length):
    """Process thinking blocks in a simple way for smaller content.
    
    Args:
        content (str): The content to process.
        max_length (int): Maximum length of thinking blocks to show.
        
    Returns:
        str: The processed content.
    """
    think_pattern = re.compile(r'<think>(.*?)</think>', re.DOTALL)
    result = content
    
    # Find all thinking blocks
    matches = list(think_pattern.finditer(content))
    
    # Process each block
    for match in reversed(matches):
        thinking_content = match.group(1)
        start, end = match.span()
        
        # Truncate if longer than max_length
        if len(thinking_content) > max_length:
            truncated = (
                thinking_content[:max_length] +
                f"\n... [Thinking truncated, {len(thinking_content) - max_length} more characters] ..."
            )
            result = result[:start] + f"<thinking>\n{truncated}\n</thinking>" + result[end:]
    
    return result


def _process_thinking_blocks_chunked(content, max_length, chunk_size):
    """Process thinking blocks in chunks for large content.
    
    Args:
        content (str): The content to process.
        max_length (int): Maximum length of thinking blocks to show.
        chunk_size (int): Size of chunks to process.
        
    Returns:
        str: The processed content.
    """
    # Use a simpler and more reliable chunking approach
    processed_chunks = []
    
    # First, split content at thinking tags to ensure we don't split within tags
    parts = re.split(r'(<think>|</think>)', content)
    
    inside_thinking = False
    current_thinking = ""
    processed_content = ""
    
    for part in parts:
        if part == "<think>":
            inside_thinking = True
            current_thinking = ""
            processed_content += part  # Keep the opening tag
        elif part == "</think>":
            inside_thinking = False
            
            # Process the thinking content if needed
            if len(current_thinking) > max_length:
                # Truncate and change tags
                truncated = (
                    current_thinking[:max_length] +
                    f"\n... [Thinking truncated, {len(current_thinking) - max_length} more characters] ..."
                )
                # Replace the last opening tag with <thinking>
                processed_content = processed_content.rstrip("<think>") + "<thinking>\n" + truncated + "\n</thinking>"
            else:
                # Keep the original thinking content
                processed_content += current_thinking + part
        elif inside_thinking:
            # Accumulate thinking content
            current_thinking += part
        else:
            # Regular content outside thinking blocks
            processed_content += part
    
    return processed_content


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
    global WORKING_DIRECTORY, SHOW_THINKING
    
    try:
        print(f"{Fore.CYAN}🤖 Local LLM Coding Assistant 🤖{Style.RESET_ALL}")
        print(f"{Fore.CYAN}================================{Style.RESET_ALL}")
        
        # Setup working directory
        default_dir = os.getcwd()  # Use current directory as default
        working_dir = input(f"{Fore.GREEN}Enter working directory path (default: current directory): {Style.RESET_ALL}")
        
        # Use default if nothing is entered
        if not working_dir.strip():
            working_dir = default_dir
            
        # Create directory if it doesn't exist
        if not os.path.exists(working_dir):
            try:
                os.makedirs(working_dir)
                print(f"{Fore.GREEN}Created working directory: {working_dir}{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}Error creating working directory: {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Using current directory as fallback.{Style.RESET_ALL}")
                working_dir = os.getcwd()
        
        # Set the global working directory
        WORKING_DIRECTORY = os.path.abspath(working_dir)
        print(f"{Fore.GREEN}Working directory set to: {WORKING_DIRECTORY}{Style.RESET_ALL}")
        
        # Change to the working directory
        os.chdir(WORKING_DIRECTORY)
        
        print("Enter your coding questions and include file paths in square brackets.")
        print("Example: How can I improve this code? [main.py]")
        print()
        print("For web searches, prefix with 'search:' or 'search ' - Example: search: Python requests library")
        print("For file editing, prefix with 'edit:' or 'edit ' - Example: edit: [main.py] to fix the function")
        print("For running commands, prefix with 'run:' or 'run ' - Example: run: the tests or run: 'python test.py'")
        print("For changing models, prefix with 'model:' or 'model ' - Example: model: llama3 or model: codellama")
        print("For creating new files, prefix with 'create:' or 'create ' - Example: create: [newfile.py]")
        print("Include URLs in brackets - Example: How to use this API? [https://api.example.com/docs]")
        print()
        print("Special commands:")
        print("  'thinking:on' or 'thinking:off' - Toggle display of AI thinking blocks")
        print("  'thinking:length N' - Set maximum length of thinking blocks (N characters)")
        print("  'timeout: N' - Set timeout for LLM operations (N seconds)")
        print("  'exit' - Quit the assistant")
        print()
        
        # Check Ollama connection
        if not check_ollama_connection():
            print(f"{Fore.RED}Exiting due to connection issues with Ollama.{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please ensure Ollama is running and accessible.{Style.RESET_ALL}")
            sys.exit(1)
        
        # Initialize conversation history
        conversation_history = []
        
        # Display current model and settings
        print(f"Current model: {CURRENT_MODEL}")
        print(f"Working directory: {WORKING_DIRECTORY}")
        print(f"Thinking display: {'ON' if SHOW_THINKING else 'OFF'}")
        print(f"Maximum thinking length: {MAX_THINKING_LENGTH} characters")
        print(f"LLM timeout: {DEFAULT_TIMEOUT} seconds")
        print()
        
        # Main chat loop
        while True:
            # Get user input
            user_input = input(f"{Fore.YELLOW}> {Style.RESET_ALL}").strip()
            
            if not user_input:
                continue
                
            # Exit commands
            if user_input.lower() in ['exit', 'quit', 'bye', ':q']:
                break
                
            # Help command
            if user_input.lower() in ['help', '?']:
                print(f"{Fore.CYAN}Available commands:{Style.RESET_ALL}")
                print("  exit: Exit the program")
                print("  help: Show this help message")
                print("  clear: Clear the terminal")
                print("  reset: Reset the conversation history")
                print("  files: Show a list of files in the current directory")
                print("  create: Create a new file")
                print("  edit: Edit a file")
                print("  run: Run a command or script")
                print("  model: Set or view the current model")
                print("  thinking:on/off: Toggle showing thinking blocks")
                print("  thinking:length: Set the max length for thinking blocks")
                print("  timeout:set: Set the timeout for API requests")
                print("  timeout:clear: Clear the timeout setting")
                print()
                print(f"{Fore.CYAN}Example queries:{Style.RESET_ALL}")
                print("  create: a simple Python script to calculate Fibonacci numbers")
                print("  edit: test.py to add error handling")
                print("  run: python3 test.py")
                print("  search: how to use async/await in Python")
                print("  plan: Create a simple Python script that prints 'Hello, World!' and run it to verify")
                print("  model: codellama")
                continue
                
            # Check for thinking display commands
            if user_input.lower() in ['thinking:on', 'thinking on']:
                # Directly set to ON instead of toggling
                SHOW_THINKING = True
                print(f"{Fore.CYAN}Thinking display is now ON{Style.RESET_ALL}")
                continue
            elif user_input.lower() in ['thinking:off', 'thinking off']:
                # Directly set to OFF instead of toggling
                SHOW_THINKING = False
                print(f"{Fore.CYAN}Thinking display is now OFF{Style.RESET_ALL}")
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
            elif user_input.lower().startswith(('timeout:', 'timeout ')):
                parts = user_input.split()
                if len(parts) >= 2:
                    set_timeout(parts[-1])
                else:
                    print(f"{Fore.YELLOW}Usage: timeout: NUMBER{Style.RESET_ALL}")
                continue
            
            # Check query type
            search_mode = is_search_query(user_input)
            edit_mode = is_edit_query(user_input)
            run_mode = is_run_query(user_input)
            model_mode = is_model_query(user_input)
            create_mode = is_create_query(user_input)
            plan_mode = is_plan_query(user_input)
            
            # Handle different query types
            try:
                if search_mode:
                    handle_search_query(user_input, conversation_history)
                elif edit_mode:
                    handle_edit_query(user_input, conversation_history)
                elif run_mode:
                    handle_run_query(user_input, conversation_history)
                elif model_mode:
                    handle_model_query(user_input, conversation_history)
                elif create_mode:
                    handle_create_query(user_input, conversation_history)
                elif plan_mode:
                    handle_plan_query(user_input, conversation_history, model=CURRENT_MODEL, timeout=DEFAULT_TIMEOUT)
                else:
                    handle_regular_query(user_input, conversation_history)
            except Exception as e:
                error_type = type(e).__name__
                print(f"{Fore.RED}Error handling query: {error_type} - {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please try again or rephrase your query.{Style.RESET_ALL}")
                # Log the error for debugging
                import traceback
                print(f"{Fore.RED}Error details:{Style.RESET_ALL}")
                traceback.print_exc()
                
                # Add error message to conversation history
                error_message = f"I encountered an error: {error_type} - {str(e)}. Please try again or rephrase your query."
                conversation_history.append({"role": "assistant", "content": error_message})
        
            except KeyboardInterrupt:
                print(f"\n{Fore.YELLOW}Operation interrupted. Type 'exit' to quit or continue with a new query.{Style.RESET_ALL}")
                continue
            except EOFError:
                print(f"\n{Fore.YELLOW}Input stream ended. Exiting...{Style.RESET_ALL}")
                break
            except Exception as e:
                error_type = type(e).__name__
                print(f"{Fore.RED}Unexpected error: {error_type} - {str(e)}{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}Please try again.{Style.RESET_ALL}")
                # Log the error for debugging
                import traceback
                traceback.print_exc()
                continue
    
    except Exception as e:
        error_type = type(e).__name__
        print(f"{Fore.RED}Critical error in main application: {error_type} - {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.RED}The application will now exit.{Style.RESET_ALL}")
        # Log the error for debugging
        import traceback
        traceback.print_exc()
        sys.exit(1)


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
        elif not os.path.exists(file_path):
            # File doesn't exist, ask if we should create it
            confirm = input(f"{Fore.YELLOW}File '{file_path}' doesn't exist. Create it? (y/n): {Style.RESET_ALL}").lower()
            if confirm == 'y':
                try:
                    # Create the directory if it doesn't exist
                    directory = os.path.dirname(file_path)
                    if directory and not os.path.exists(directory):
                        os.makedirs(directory)
                    
                    # Create an empty file
                    Path(file_path).touch()
                    print(f"{Fore.GREEN}Created '{file_path}'.{Style.RESET_ALL}")
                    files_content_section += f"File: {file_path}\nContent:\n[New empty file]\n\n"
                    
                    # Add the file creation to conversation history
                    conversation_history.append({"role": "system", "content": f"Created file '{file_path}'."})
                except Exception as e:
                    print(f"{Fore.RED}Error creating '{file_path}': {e}{Style.RESET_ALL}")
                    return
            else:
                print(f"{Fore.YELLOW}Edit cancelled for '{file_path}'.{Style.RESET_ALL}")
                return
    
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
                original_content = read_file_content(file_path, None, None) or ""  # Use empty string for new files
                
                if original_content != modified_content:
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
    
    # Extract file paths from the query
    clean_query, file_items, _ = extract_file_paths_and_urls(run_query)
    
    # Construct user message
    user_message = f"Command Request: {clean_query}\n"
    user_message += "Please suggest a command to run based on this request. "
    user_message += "Format your response with the command in a code block using triple backticks."
    
    # Include file contents if specified
    if file_items:
        user_message += "\n\nFiles:\n"
        for file_item in file_items:
            # Get the file path
            if isinstance(file_item, tuple):
                file_path, start_line, end_line = file_item
            else:
                file_path, start_line, end_line = file_item, None, None
            
            # Read the file content
            content = read_file_content(file_path, start_line, end_line)
            if content:
                # Include line range info in the file header if specified
                if start_line is not None or end_line is not None:
                    line_info = f" (lines {start_line or '1'}-{end_line or 'end'})"
                    user_message += f"File: {file_path}{line_info}\nContent:\n{content}\n\n"
                else:
                    user_message += f"File: {file_path}\nContent:\n{content}\n\n"
    
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
        is_safe, reason = is_safe_command(suggested_command)
        if not is_safe:
            print(f"{Fore.RED}Warning: The suggested command may be unsafe: {suggested_command}{Style.RESET_ALL}")
            print(f"{Fore.RED}Reason: {reason}{Style.RESET_ALL}")
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
    
    # Special case for listing models
    if model_name == "list":
        try:
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                available_models = [model.get("name") for model in response.json().get("models", [])]
                if available_models:
                    print(f"{Fore.CYAN}Available models:{Style.RESET_ALL}")
                    for model in available_models:
                        if model == CURRENT_MODEL:
                            print(f"{Fore.GREEN}* {model} (current){Style.RESET_ALL}")
                        else:
                            print(f"  {model}")
                    
                    # Let the user select a model
                    print()
                    print(f"{Fore.CYAN}Current model: {CURRENT_MODEL}{Style.RESET_ALL}")
                    new_model = input(f"{Fore.GREEN}Select a model (leave empty to keep current): {Style.RESET_ALL}")
                    
                    if not new_model.strip():
                        print(f"{Fore.YELLOW}No change. Still using model: {CURRENT_MODEL}{Style.RESET_ALL}")
                        return
                    
                    # Update model_name for the rest of the function
                    model_name = new_model.strip()
                else:
                    print(f"{Fore.YELLOW}No models found.{Style.RESET_ALL}")
                    return
            else:
                print(f"{Fore.YELLOW}Could not retrieve model list. HTTP {response.status_code}{Style.RESET_ALL}")
                return
        except requests.exceptions.RequestException as e:
            print(f"{Fore.YELLOW}Error retrieving model list: {e}{Style.RESET_ALL}")
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


def handle_create_query(user_input, conversation_history):
    """Handle file creation queries."""
    create_query = extract_create_query(user_input)
    clean_query, file_items, _ = extract_file_paths_and_urls(create_query)
    
    if not file_items:
        print(f"{Fore.YELLOW}No file path specified. Use [file_path] with create:.{Style.RESET_ALL}")
        return
    
    for file_item in file_items:
        if isinstance(file_item, tuple):
            file_path = file_item[0]
        else:
            file_path = file_item
        
        # Ensure the file path is within the working directory if set
        if WORKING_DIRECTORY and not os.path.isabs(file_path):
            file_path = os.path.join(WORKING_DIRECTORY, file_path)
        elif WORKING_DIRECTORY and os.path.isabs(file_path):
            # Check if the absolute path is within the working directory
            if not os.path.abspath(file_path).startswith(WORKING_DIRECTORY):
                error_msg = f"Error: Cannot create '{file_path}' as it is outside the working directory. Access denied."
                print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
                continue
            
        if os.path.exists(file_path):
            print(f"{Fore.YELLOW}File '{file_path}' already exists.{Style.RESET_ALL}")
            confirm = input(f"{Fore.YELLOW}Overwrite with an empty file? (y/n): {Style.RESET_ALL}").lower()
            if confirm != 'y':
                print(f"{Fore.YELLOW}File creation cancelled for '{file_path}'.{Style.RESET_ALL}")
                continue
        
        confirm = input(f"{Fore.YELLOW}Create '{file_path}'? (y/n): {Style.RESET_ALL}").lower()
        if confirm == 'y':
            try:
                # Create parent directories if they don't exist
                parent_dir = os.path.dirname(file_path)
                if parent_dir and not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)
                    print(f"{Fore.GREEN}Created directory: {parent_dir}{Style.RESET_ALL}")
                
                Path(file_path).touch()
                print(f"{Fore.GREEN}Created '{file_path}'.{Style.RESET_ALL}")
                conversation_history.append({"role": "system", "content": f"Created file '{file_path}'."})
            except Exception as e:
                print(f"{Fore.RED}Error creating '{file_path}': {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.YELLOW}File creation cancelled for '{file_path}'.{Style.RESET_ALL}")


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


def handle_plan_query(user_input, conversation_history, model=None, timeout=None):
    """
    Handle planning queries by breaking down high-level requests into executable steps.
    The steps are presented to the user for review and can be executed with confirmation.
    
    Args:
        user_input (str): The user's planning query
        conversation_history (list): The conversation history
        model (str, optional): The model to use for generating the plan
        timeout (int, optional): The timeout for API requests in seconds
    """
    import json
    from pathlib import Path
    import subprocess
    
    # Extract the plan description from the query
    plan_description = extract_plan_query(user_input)
    
    # Extract file paths from the query for providing context
    # Use a regex to find file paths in square brackets
    import re
    file_paths = re.findall(r'\[([^\]]+)\]', user_input)
    
    # Read the contents of the specified files for context
    file_contents = {}
    for file_path in file_paths:
        content = read_file_content(file_path)
        if content:
            file_contents[file_path] = content
        else:
            print(f"{Fore.YELLOW}Warning: Could not read file {file_path}{Style.RESET_ALL}")
    
    # Construct the file context section if any files were successfully read
    file_context = ""
    if file_contents:
        file_context = "Files for context:\n\n"
        for file_path, content in file_contents.items():
            file_context += f"--- {file_path} ---\n{content}\n\n"
    
    # STEP 1: Analysis phase - Ask the model to understand the task without requiring a specific output format
    analysis_prompt = f"""You are an AI assistant helping a user to implement a project. The user's request is: {plan_description}

{file_context}Your task is to analyze this request and understand what needs to be done. 
Think about the approach you would take to implement this request, but DO NOT output a plan yet.
Just analyze the requirements, potential code structures, and approach.

Keep your response relatively brief - focus on understanding the task, not implementing it yet.
"""
    
    # Add the analysis prompt to the conversation history
    conversation_history.append({"role": "user", "content": analysis_prompt})
    
    # Print "Analyzing request..." to indicate processing
    print(f"{Fore.CYAN}Analyzing request...{Style.RESET_ALL}")
    
    # Get the response from Ollama for the analysis phase
    analysis_response = get_ollama_response(conversation_history, model=model, timeout=timeout)
    
    if not analysis_response:
        print(f"{Fore.RED}Failed to get an analysis from the model.{Style.RESET_ALL}")
        return
    
    # Process thinking blocks for display
    processed_analysis = process_thinking_blocks(analysis_response)
    print(f"{Fore.GREEN}Analysis:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{processed_analysis}{Style.RESET_ALL}")
    
    # Add the assistant's analysis to the conversation history
    conversation_history.append({"role": "assistant", "content": analysis_response})
    
    # STEP 2: Planning phase - Now ask for a concise, structured plan with minimal thinking
    # Configure a payload with options that encourage short, focused output
    planning_prompt = f"""Now, based on your analysis, provide a step-by-step plan to implement the request.
Your task is to break down this request into a sequence of steps that the program can execute. Each step should be one of the following types:

create_file: with 'file_path' parameter, which is a path relative to the working directory.
write_code: with 'file_path' and 'code' parameters. 'file_path' is relative to the working directory, and 'code' is the exact code to write to the file, which will overwrite any existing content.
edit_file: with 'file_path', 'original_pattern', and 'new_content' parameters. This will find the original_pattern in the file and replace it with new_content.
run_command: with 'command' parameter, which is the command to run in the working directory.
run_command_and_check: with 'command' and 'expected_output' parameters, to run the command and verify the output.

YOU MUST RESPOND WITH ONLY A JSON ARRAY containing steps with these exact formats:
1. {{"type": "create_file", "file_path": "example.py"}}
2. {{"type": "write_code", "file_path": "example.py", "code": "print('Hello')"}}
3. {{"type": "edit_file", "file_path": "example.py", "original_pattern": "print('Hello')", "new_content": "print('Hello World')"}}
4. {{"type": "run_command", "command": "python example.py"}}
5. {{"type": "run_command_and_check", "command": "python example.py", "expected_output": "Hello"}}

IMPORTANT: Keep your response EXTREMELY CONCISE. ONLY return a valid JSON array of steps, nothing else. NO explanations, NO thinking, NO markdown.
"""
    
    # Add the planning prompt to the conversation history
    conversation_history.append({"role": "user", "content": planning_prompt})
    
    # Print "Generating plan..." to indicate processing
    print(f"{Fore.CYAN}Generating plan...{Style.RESET_ALL}")
    
    # Get the response from Ollama with specific options to encourage brief output
    try:
        # Prepare the request payload with options to limit response size
        payload = {
            "model": model or CURRENT_MODEL,
            "messages": conversation_history,
            "stream": False,
            "options": {
                "max_tokens": 2000,    # Set a tighter limit for the plan
                "temperature": 0.1,    # Lower temperature for more deterministic output
                "top_p": 0.1           # Narrow token selection for more focused output
            }
        }
        
        # Send a direct request to the Ollama API
        response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout or DEFAULT_TIMEOUT)
        
        # Process the response
        if response.status_code == 200:
            response_json = response.json()
            plan_response = response_json.get("message", {}).get("content", "")
        else:
            print(f"{Fore.RED}Error: Received status code {response.status_code} from Ollama API{Style.RESET_ALL}")
            print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
            return
    except Exception as e:
        print(f"{Fore.RED}Error during plan generation: {str(e)}{Style.RESET_ALL}")
        return
    
    if not plan_response:
        print(f"{Fore.RED}Failed to get a plan from the model.{Style.RESET_ALL}")
        return
    
    # Process thinking blocks for display but don't print raw response yet
    processed_response = process_thinking_blocks(plan_response)
    # We'll only show the formatted plan, not the raw JSON
    
    # Add the assistant's response to the conversation history
    conversation_history.append({"role": "assistant", "content": plan_response})
    
    # Try to extract JSON from the response
    steps = None
    retry_needed = False
    
    try:
        # Clean the response from thinking blocks and other non-JSON artifacts
        import re
        
        # Create a copy of the response for JSON extraction
        # This way we preserve the original response with thinking blocks
        json_extraction_response = plan_response
        
        # First, check for mismatched thinking tags which would cause problems
        think_open_count = json_extraction_response.count("<think>")
        think_close_count = json_extraction_response.count("</think>")
        
        # More robust thinking block removal
        if think_open_count != think_close_count:
            # If tags don't match, use our split-based approach which is more reliable
            parts = re.split(r'(<think>|</think>)', json_extraction_response)
            inside_thinking = False
            clean_parts = []
            
            for part in parts:
                if part == "<think>":
                    inside_thinking = True
                elif part == "</think>":
                    inside_thinking = False
                elif not inside_thinking:
                    clean_parts.append(part)
            
            json_extraction_response = ''.join(clean_parts)
        else:
            # If tags match properly, we can use the regex approach
            json_extraction_response = re.sub(r'<think>.*?</think>', '', json_extraction_response, flags=re.DOTALL)
        
        # Remove standalone think tags that might remain
        json_extraction_response = re.sub(r'</think>', '', json_extraction_response)
        json_extraction_response = re.sub(r'<think>', '', json_extraction_response)
        
        # Remove common text artifacts
        json_extraction_response = re.sub(r'```.*?```', '', json_extraction_response, flags=re.DOTALL)
        json_extraction_response = re.sub(r'Here is the JSON array:|Here are the steps:|Steps:', '', json_extraction_response)
        
        # Find JSON in the cleaned response
        json_start = json_extraction_response.find("[")
        json_end = json_extraction_response.rfind("]") + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = json_extraction_response[json_start:json_end]
            
            # Try to fix common JSON syntax errors before parsing
            # Fix missing quotes before keys
            json_str = re.sub(r'{\s*([a-zA-Z0-9_]+)":', r'{"\1":', json_str)
            # Fix missing commas between objects
            json_str = re.sub(r'}\s*{', r'},{', json_str)
            
            steps = json.loads(json_str)
        else:
            # Try to extract from code blocks in the original response
            code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", plan_response)
            if code_blocks:
                json_str = code_blocks[0]
                
                # Apply the same fixes to code blocks
                json_str = re.sub(r'{\s*([a-zA-Z0-9_]+)":', r'{"\1":', json_str)
                json_str = re.sub(r'}\s*{', r'},{', json_str)
                
                steps = json.loads(json_str)
            else:
                retry_needed = True
                raise ValueError("No valid JSON found in the response")
    except (json.JSONDecodeError, ValueError) as e:
        if not retry_needed:
            print(f"{Fore.RED}Failed to parse the plan: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Raw response:{Style.RESET_ALL}")
            print(plan_response)
        retry_needed = True
    
    # If we couldn't extract valid JSON, retry with the same prompt
    if retry_needed:
        print(f"{Fore.YELLOW}The model didn't return a valid JSON plan. Retrying...{Style.RESET_ALL}")
        
        # Add the same planning prompt to the conversation history for retry
        conversation_history.append({"role": "user", "content": planning_prompt})
        
        # Print "Retrying plan generation..." to indicate processing
        print(f"{Fore.CYAN}Retrying plan generation...{Style.RESET_ALL}")
        
        # Get the response from Ollama with even stricter parameters
        try:
            # Prepare the request payload with stricter options
            payload = {
                "model": model or CURRENT_MODEL,
                "messages": conversation_history,
                "stream": False,
                "options": {
                    "max_tokens": 2000,    # Same tight limit
                    "temperature": 0.0,    # Zero temperature for maximum determinism
                    "top_p": 0.05          # Even narrower token selection
                }
            }
            
            # Send a direct request to the Ollama API
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout or DEFAULT_TIMEOUT)
            
            # Process the response
            if response.status_code == 200:
                response_json = response.json()
                plan_response = response_json.get("message", {}).get("content", "")
            else:
                print(f"{Fore.RED}Error: Received status code {response.status_code} from Ollama API{Style.RESET_ALL}")
                print(f"{Fore.RED}Response: {response.text}{Style.RESET_ALL}")
                return
        except Exception as e:
            print(f"{Fore.RED}Error during retry plan generation: {str(e)}{Style.RESET_ALL}")
            return
        
        if not plan_response:
            print(f"{Fore.RED}Failed to get a plan from the model on retry.{Style.RESET_ALL}")
            return
        
        # Process thinking blocks for display but don't print raw response yet
        processed_response = process_thinking_blocks(plan_response)
        # We'll only show the formatted plan, not the raw JSON
        
        # Add the assistant's retry response to the conversation history
        conversation_history.append({"role": "assistant", "content": plan_response})
        
        # Try to extract JSON from the retry response
        try:
            # Create a copy of the response for JSON extraction
            json_extraction_response = plan_response
            
            # First, check for mismatched thinking tags which would cause problems
            think_open_count = json_extraction_response.count("<think>")
            think_close_count = json_extraction_response.count("</think>")
            
            # More robust thinking block removal
            if think_open_count != think_close_count:
                # If tags don't match, use our split-based approach which is more reliable
                parts = re.split(r'(<think>|</think>)', json_extraction_response)
                inside_thinking = False
                clean_parts = []
                
                for part in parts:
                    if part == "<think>":
                        inside_thinking = True
                    elif part == "</think>":
                        inside_thinking = False
                    elif not inside_thinking:
                        clean_parts.append(part)
                
                json_extraction_response = ''.join(clean_parts)
            else:
                # If tags match properly, we can use the regex approach
                json_extraction_response = re.sub(r'<think>.*?</think>', '', json_extraction_response, flags=re.DOTALL)
            
            # Remove standalone think tags that might remain
            json_extraction_response = re.sub(r'</think>', '', json_extraction_response)
            json_extraction_response = re.sub(r'<think>', '', json_extraction_response)
            
            # Remove common text artifacts
            json_extraction_response = re.sub(r'```.*?```', '', json_extraction_response, flags=re.DOTALL)
            json_extraction_response = re.sub(r'Here is the JSON array:|Here are the steps:|Steps:', '', json_extraction_response)
            
            # Find JSON in the cleaned response
            json_start = json_extraction_response.find("[")
            json_end = json_extraction_response.rfind("]") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = json_extraction_response[json_start:json_end]
                
                # Try to fix common JSON syntax errors before parsing
                # Fix missing quotes before keys
                json_str = re.sub(r'{\s*([a-zA-Z0-9_]+)":', r'{"\1":', json_str)
                # Fix missing commas between objects
                json_str = re.sub(r'}\s*{', r'},{', json_str)
                
                steps = json.loads(json_str)
            else:
                # Try to extract from code blocks in the original response
                code_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", plan_response)
                if code_blocks:
                    json_str = code_blocks[0]
                    
                    # Apply the same fixes to code blocks
                    json_str = re.sub(r'{\s*([a-zA-Z0-9_]+)":', r'{"\1":', json_str)
                    json_str = re.sub(r'}\s*{', r'},{', json_str)
                    
                    steps = json.loads(json_str)
                else:
                    print(f"{Fore.RED}No valid JSON found in the retry response.{Style.RESET_ALL}")
                    return
        except (json.JSONDecodeError, ValueError) as e:
            print(f"{Fore.RED}Failed to parse the plan after retry: {str(e)}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Raw response from retry:{Style.RESET_ALL}")
            print(plan_response)
            return

    if not steps:
        print(f"{Fore.RED}Could not extract a valid plan from the model's response.{Style.RESET_ALL}")
        return
    
    # Display the plan to the user
    print(f"{Fore.GREEN}Generated Plan:{Style.RESET_ALL}")
    for i, step in enumerate(steps, 1):
        step_type = step.get("type")
        if step_type == "create_file":
            print(f"{i}. Create file: {step.get('file_path')}")
        elif step_type == "write_code":
            print(f"{i}. Write code to: {step.get('file_path')}")
            print(f"   Code snippet: {step.get('code')[:50]}..." if len(step.get('code', '')) > 50 else f"   Code: {step.get('code')}")
        elif step_type == "edit_file":
            print(f"{i}. Edit file: {step.get('file_path')}")
            print(f"   Find: {step.get('original_pattern')[:30]}..." if len(step.get('original_pattern', '')) > 30 else f"   Find: {step.get('original_pattern')}")
            print(f"   Replace with: {step.get('new_content')[:30]}..." if len(step.get('new_content', '')) > 30 else f"   Replace with: {step.get('new_content')}")
        elif step_type == "run_command":
            print(f"{i}. Run command: {step.get('command')}")
        elif step_type == "run_command_and_check":
            print(f"{i}. Run and check: {step.get('command')}")
            print(f"   Expected output: {step.get('expected_output')}")
        else:
            print(f"{i}. Unknown step type: {step_type}")
    
    # Ask if the user wants to save the plan
    save_plan = input(f"{Fore.YELLOW}Do you want to save this plan to a file? (y/n): {Style.RESET_ALL}")
    if save_plan.lower() == 'y':
        plan_file = input(f"{Fore.YELLOW}Enter filename to save the plan (default: steps.json): {Style.RESET_ALL}")
        if not plan_file:
            plan_file = "steps.json"
        
        try:
            with open(plan_file, 'w') as f:
                json.dump(steps, f, indent=2)
            print(f"{Fore.GREEN}Plan saved to {plan_file}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}Failed to save plan: {str(e)}{Style.RESET_ALL}")
    
    # Execute steps with user confirmation
    proceed = input(f"{Fore.YELLOW}Do you want to start executing the plan? (y/n): {Style.RESET_ALL}")
    if proceed.lower() != 'y':
        return
    
    # Execute each step
    for i, step in enumerate(steps, 1):
        step_type = step.get("type")
        
        # Display the current step
        if step_type == "create_file":
            print(f"{Fore.CYAN}Step {i}: Create file {step.get('file_path')}{Style.RESET_ALL}")
            
            file_path = step.get('file_path')
            file = Path(file_path)
            
            if file.exists():
                overwrite = input(f"{Fore.YELLOW}File {file_path} already exists. Do you want to overwrite it with an empty file? (y/n): {Style.RESET_ALL}")
                if overwrite.lower() != 'y':
                    print(f"{Fore.YELLOW}File creation skipped.{Style.RESET_ALL}")
                    continue
            
            # Create the directory if it doesn't exist
            file.parent.mkdir(parents=True, exist_ok=True)
            file.touch()
            print(f"{Fore.GREEN}Created empty file: {file_path}{Style.RESET_ALL}")
            confirm = input(f"{Fore.YELLOW}Continue with the next steps? (y/n): {Style.RESET_ALL}")
            if confirm.lower() != 'y':
                break
            continue
        elif step_type == "write_code":
            print(f"{Fore.CYAN}Step {i}: Write code to {step.get('file_path')}{Style.RESET_ALL}")
            print(f"Code to write:\n{step.get('code')}")
            
            file_path = step.get('file_path')
            code = step.get('code')
            file = Path(file_path)
            
            confirm = input(f"{Fore.YELLOW}Do you want to execute this step? (y/n): {Style.RESET_ALL}")
            if confirm.lower() == 'y':
                if file.exists():
                    overwrite = input(f"{Fore.YELLOW}File {file_path} already exists. Do you want to overwrite it? (y/n): {Style.RESET_ALL}")
                    if overwrite.lower() != 'y':
                        print(f"{Fore.YELLOW}Writing code skipped.{Style.RESET_ALL}")
                        continue
                
                # Create the directory if it doesn't exist
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(code)
                print(f"{Fore.GREEN}Code written to: {file_path}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}Step skipped.{Style.RESET_ALL}")
            
            confirm = input(f"{Fore.YELLOW}Continue with the next steps? (y/n): {Style.RESET_ALL}")
            if confirm.lower() != 'y':
                break
            continue
        elif step_type == "edit_file":
            print(f"{Fore.CYAN}Step {i}: Edit file {step.get('file_path')}{Style.RESET_ALL}")
            print(f"Find: {step.get('original_pattern')}")
            print(f"Replace with: {step.get('new_content')}")
            
            # Read the current content of the file
            file_path = step.get('file_path')
            original_pattern = step.get('original_pattern')
            new_content = step.get('new_content')
            
            current_content = read_file_content(file_path)
            if current_content is None:
                print(f"{Fore.RED}Could not read file {file_path} for editing.{Style.RESET_ALL}")
                continue
                
            # Check if the pattern exists in the file
            if original_pattern in current_content:
                # Generate a preview of the changes
                updated_content = current_content.replace(original_pattern, new_content)
                diff = generate_colored_diff(current_content, updated_content, file_path)
                print(f"{Fore.CYAN}Changes preview:{Style.RESET_ALL}")
                print(diff)
                
                # Ask for confirmation
                confirm = input(f"{Fore.YELLOW}Do you want to apply these changes? (y/n): {Style.RESET_ALL}")
                if confirm.lower() == 'y':
                    # Apply the changes
                    if write_file_content(file_path, updated_content):
                        print(f"{Fore.GREEN}File {file_path} edited successfully.{Style.RESET_ALL}")
                        conversation_history.append({
                            "role": "system", 
                            "content": f"The file '{file_path}' was edited, replacing '{original_pattern}' with '{new_content}'."
                        })
                    else:
                        print(f"{Fore.RED}Failed to write changes to {file_path}.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.YELLOW}Changes cancelled for {file_path}.{Style.RESET_ALL}")
            else:
                print(f"{Fore.RED}The pattern to replace was not found in {file_path}.{Style.RESET_ALL}")
                # Ask if the user wants to see the file content
                view_content = input(f"{Fore.YELLOW}Do you want to view the current file content? (y/n): {Style.RESET_ALL}")
                if view_content.lower() == 'y':
                    print(f"{Fore.CYAN}Current content of {file_path}:{Style.RESET_ALL}")
                    print(current_content)
        elif step_type == "run_command":
            print(f"{Fore.CYAN}Step {i}: Run command: {step.get('command')}{Style.RESET_ALL}")
            confirm = input(f"{Fore.YELLOW}Do you want to execute this step? (y/n): {Style.RESET_ALL}")
            if confirm.lower() == 'y':
                print(f"{Fore.CYAN}Executing: {step.get('command')}{Style.RESET_ALL}")
                
                # Use subprocess.run directly for consistency with tests
                command = step.get('command')
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"{Fore.GREEN}Command executed successfully:{Style.RESET_ALL}")
                    print(result.stdout)
                else:
                    print(f"{Fore.RED}Command failed with error code {result.returncode}:{Style.RESET_ALL}")
                    print(result.stderr)
                
                conversation_history.append({
                    "role": "system", 
                    "content": f"The command '{command}' was executed with the following output:\n{result.stdout if result.returncode == 0 else result.stderr}"
                })
            else:
                print(f"{Fore.YELLOW}Step skipped.{Style.RESET_ALL}")
            
            confirm = input(f"{Fore.YELLOW}Continue with the next steps? (y/n): {Style.RESET_ALL}")
            if confirm.lower() != 'y':
                break
            continue
        elif step_type == "run_command_and_check":
            print(f"{Fore.CYAN}Step {i}: Run and check: {step.get('command')}{Style.RESET_ALL}")
            print(f"Expected output: {step.get('expected_output')}")
            confirm = input(f"{Fore.YELLOW}Do you want to execute this step? (y/n): {Style.RESET_ALL}")
            if confirm.lower() == 'y':
                print(f"{Fore.CYAN}Executing: {step.get('command')}{Style.RESET_ALL}")
                
                # Use subprocess.run directly
                command = step.get('command')
                expected_output = step.get('expected_output')
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"{Fore.GREEN}Command executed successfully:{Style.RESET_ALL}")
                    print(result.stdout)
                    
                    # Check if the output matches the expected output
                    if result.stdout.strip() == expected_output.strip():
                        print(f"{Fore.GREEN}Test passed! Output matches expected output.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.RED}Test failed.{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Expected: {expected_output}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Actual: {result.stdout}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Command failed with error code {result.returncode}:{Style.RESET_ALL}")
                    print(result.stderr)
                
                conversation_history.append({
                    "role": "system", 
                    "content": f"The command '{command}' was executed with the following output:\n{result.stdout if result.returncode == 0 else result.stderr}"
                })
            else:
                print(f"{Fore.YELLOW}Step skipped.{Style.RESET_ALL}")
            
            confirm = input(f"{Fore.YELLOW}Continue with the next steps? (y/n): {Style.RESET_ALL}")
            if confirm.lower() != 'y':
                break
            continue
        else:
            print(f"{Fore.RED}Unknown step type: {step_type}. Skipping.{Style.RESET_ALL}")
            continue
        
        # Ask if the user wants to continue with the next steps
        continue_plan = input(f"{Fore.YELLOW}Continue with the next steps? (y/n): {Style.RESET_ALL}")
        if continue_plan.lower() != 'y':
            break
    
    print(f"{Fore.GREEN}Plan execution completed.{Style.RESET_ALL}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting gracefully...")
        sys.exit(0) 