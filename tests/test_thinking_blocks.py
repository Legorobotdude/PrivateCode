#!/usr/bin/env python3
"""
Test script for the thinking blocks functionality in the code assistant.
"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock
import tempfile

# Add the parent directory to the path so we can import code_assistant
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import code_assistant


class TestThinkingBlocks(unittest.TestCase):
    """Test the thinking blocks functionality."""

    def setUp(self):
        """Set up the test environment."""
        # Save original values
        self.original_show_thinking = code_assistant.SHOW_THINKING
        self.original_max_thinking_length = code_assistant.MAX_THINKING_LENGTH

    def tearDown(self):
        """Clean up after the test."""
        # Restore original values
        code_assistant.SHOW_THINKING = self.original_show_thinking
        code_assistant.MAX_THINKING_LENGTH = self.original_max_thinking_length

    def test_process_thinking_blocks_hidden(self):
        """Test that thinking blocks are hidden by default."""
        code_assistant.SHOW_THINKING = False
        
        # Test with a simple thinking block
        content = "Hello, <think>This is a thinking block</think> world!"
        result = code_assistant.process_thinking_blocks(content)
        self.assertEqual(result, "Hello,  world!")
        
        # Test with multiple thinking blocks
        content = "Start <think>First thinking</think> middle <think>Second thinking</think> end."
        result = code_assistant.process_thinking_blocks(content)
        self.assertEqual(result, "Start  middle  end.")
        
        # Test with no thinking blocks
        content = "No thinking blocks here."
        result = code_assistant.process_thinking_blocks(content)
        self.assertEqual(result, "No thinking blocks here.")
        
        # Test with a very large thinking block
        large_thinking = "X" * 10000
        content = f"Start <think>{large_thinking}</think> end."
        result = code_assistant.process_thinking_blocks(content)
        self.assertEqual(result, "Start  end.")

    def test_process_thinking_blocks_shown(self):
        """Test that thinking blocks are shown when enabled."""
        code_assistant.SHOW_THINKING = True
        
        # Test with a simple thinking block
        content = "Hello, <think>This is a thinking block</think> world!"
        result = code_assistant.process_thinking_blocks(content)
        self.assertTrue("<think>This is a thinking block</think>" in result)
        
        # Test with multiple thinking blocks
        content = "Start <think>First thinking</think> middle <think>Second thinking</think> end."
        result = code_assistant.process_thinking_blocks(content)
        self.assertTrue("<think>First thinking</think>" in result)
        self.assertTrue("<think>Second thinking</think>" in result)
        
        # Verify that non-truncated thinking blocks keep their original <think> tags
        # and only truncated blocks get <thinking> tags
        code_assistant.MAX_THINKING_LENGTH = 5
        content = "Regular <think>Short</think> and <think>Very long thinking</think>."
        result = code_assistant.process_thinking_blocks(content)
        self.assertTrue("<think>Short</think>" in result)  # Short block keeps original tags
        self.assertTrue("<thinking>" in result)  # Long block gets converted to <thinking> tags
        self.assertTrue("[Thinking truncated" in result)  # Long block gets truncated message

    def test_process_thinking_blocks_truncated(self):
        """Test that thinking blocks are truncated when too long."""
        code_assistant.SHOW_THINKING = True
        code_assistant.MAX_THINKING_LENGTH = 10
        
        # Test with a thinking block longer than the max length
        content = "Hello, <think>This is a very long thinking block that should be truncated</think> world!"
        result = code_assistant.process_thinking_blocks(content)
        self.assertTrue("<thinking>" in result)  # Truncated blocks are wrapped in <thinking> tags
        self.assertTrue("[Thinking truncated" in result)
        self.assertTrue("world!" in result)
        
        # Test with a very large thinking block
        large_thinking = "X" * 10000
        content = f"Start <think>{large_thinking}</think> end."
        result = code_assistant.process_thinking_blocks(content)
        self.assertTrue("<thinking>" in result)  # Truncated blocks are wrapped in <thinking> tags
        self.assertTrue("[Thinking truncated" in result)
        self.assertTrue("end." in result)

    def test_toggle_thinking_display(self):
        """Test toggling the thinking display."""
        # Start with thinking hidden
        code_assistant.SHOW_THINKING = False
        
        # Toggle to show thinking
        code_assistant.toggle_thinking_display()
        self.assertTrue(code_assistant.SHOW_THINKING)
        
        # Toggle back to hide thinking
        code_assistant.toggle_thinking_display()
        self.assertFalse(code_assistant.SHOW_THINKING)

    def test_set_thinking_max_length(self):
        """Test setting the maximum thinking length."""
        # Set a valid length
        code_assistant.set_thinking_max_length(2000)
        self.assertEqual(code_assistant.MAX_THINKING_LENGTH, 2000)
        
        # Set a length that's too small
        code_assistant.set_thinking_max_length(50)
        self.assertEqual(code_assistant.MAX_THINKING_LENGTH, 100)  # Should be set to minimum of 100

    @patch('builtins.print')
    def test_extract_suggested_command_with_thinking(self, mock_print):
        """Test extracting a suggested command with thinking blocks."""
        # Command with thinking block
        response = """
        <think>
        I need to suggest a command to list files in the directory.
        The 'ls' command is commonly used for this in Unix-like systems.
        For Windows, 'dir' is more appropriate.
        Since the user is on Windows, I'll suggest 'dir'.
        </think>
        
        You can list the files in your directory with:
        
        ```
        dir
        ```
        """
        
        # With thinking hidden
        code_assistant.SHOW_THINKING = False
        command = code_assistant.extract_suggested_command(response)
        self.assertEqual(command, "dir")
        
        # With thinking shown
        code_assistant.SHOW_THINKING = True
        command = code_assistant.extract_suggested_command(response)
        self.assertEqual(command, "dir")

    def test_debug_large_thinking_truncation(self):
        """A simplified test to debug the thinking truncation issue."""
        # Setup
        code_assistant.SHOW_THINKING = True
        code_assistant.MAX_THINKING_LENGTH = 10  # Very small limit to ensure truncation
        
        # Create a moderately large thinking block (should be smaller than chunk_size)
        thinking_content = "X" * 1000  # 1000 Xs
        content = f"Before <think>{thinking_content}</think> After"
        
        # Process the content
        result = code_assistant.process_thinking_blocks(content)
        
        # Print debug info to help us understand what's happening
        print(f"\nDEBUG - Result length: {len(result)}")
        print(f"DEBUG - Original length: {len(content)}")
        print(f"DEBUG - Contains '<thinking>': {'<thinking>' in result}")
        print(f"DEBUG - Contains '<think>': {'<think>' in result}")
        print(f"DEBUG - Contains 'truncated': {'truncated' in result}")
        print(f"DEBUG - First 50 chars: {result[:50]}")
        print(f"DEBUG - Last 50 chars: {result[-50:]}")
        
        # Check if the thinking was properly truncated
        self.assertTrue("<thinking>" in result)
        self.assertFalse("<think>" in result)  # Original tag should be gone
        self.assertTrue("[Thinking truncated" in result)
        self.assertTrue("Before" in result)
        self.assertTrue("After" in result)

    def test_large_response_with_thinking_blocks(self):
        """Test processing an extremely large response with multiple thinking blocks."""
        # Create a very large response with a single massive thinking block
        normal_text_before = "Text before thinking block. " * 200  # 4,000+ chars of text before
        
        # Create a single massive thinking block of ~50,000 chars
        thinking_content = "This is a very large thinking block. " * 2500  # ~50,000 chars
        large_thinking_block = f"<think>{thinking_content}</think>"
        
        normal_text_after = "Text after thinking block. " * 200  # 4,000+ chars of text after
        
        # Combine into a response with ~58,000 chars total
        large_response = normal_text_before + large_thinking_block + normal_text_after
        
        # Test with thinking disabled
        code_assistant.SHOW_THINKING = False
        result = code_assistant.process_thinking_blocks(large_response)
        
        # Verify the thinking block was completely removed
        self.assertNotIn("<think>", result)
        self.assertNotIn("</think>", result)
        self.assertNotIn("This is a very large thinking block", result)
        
        # Verify normal content is preserved exactly as it was
        self.assertEqual(result, normal_text_before + normal_text_after)
        
        # Test with thinking enabled
        code_assistant.SHOW_THINKING = True
        result = code_assistant.process_thinking_blocks(large_response)
        
        # Verify thinking block is present but truncated - using <thinking> tags for truncated content
        self.assertIn("<thinking>", result)
        self.assertIn("</thinking>", result)
        self.assertIn("[Thinking truncated", result)
        self.assertIn("This is a very large thinking block", result)
        
        # Verify the block was actually truncated by checking length
        self.assertTrue(len(result) < len(large_response))


if __name__ == '__main__':
    unittest.main() 