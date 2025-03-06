import code_assistant
import tempfile
import os

# Create a test file with multiple lines
test_content = "\n".join([f"Line {i}: This is test content line {i}" for i in range(1, 101)])
test_file = tempfile.mktemp()

try:
    # Write the test content to the file
    with open(test_file, 'w') as f:
        f.write(test_content)
    
    # Test reading a single line
    print("Testing reading line 42:")
    content = code_assistant.read_file_content(test_file, 42, 43)
    print(content)
    
    # Check if the content contains the expected line
    assert "Line 42:" in content, "Line 42 not found in content"
    assert "Line 41:" not in content, "Line 41 found in content"
    assert "Line 43:" not in content, "Line 43 found in content"
    
    print("\nTesting reading line 42 with end_line=None:")
    content = code_assistant.read_file_content(test_file, 42, None)
    print(content[:200] + "..." if len(content) > 200 else content)
    
    print("\nTesting reading a single line with just start_line:")
    content = code_assistant.read_file_content(test_file, 42, 42 + 1)
    print(content)
    
    print("\nSuccess!")
finally:
    # Clean up the test file
    if os.path.exists(test_file):
        os.remove(test_file) 