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

    def test_process_thinking_blocks_truncated(self):
        """Test that thinking blocks are truncated when too long."""
        code_assistant.SHOW_THINKING = True
        code_assistant.MAX_THINKING_LENGTH = 10
        
        # Test with a thinking block longer than the max length
        content = "Hello, <think>This is a very long thinking block that should be truncated</think> world!"
        result = code_assistant.process_thinking_blocks(content)
        self.assertTrue("<thinking>" in result)
        self.assertTrue("[Thinking truncated" in result)
        self.assertTrue("world!" in result)
        
        # Test with a very large thinking block
        large_thinking = "X" * 10000
        content = f"Start <think>{large_thinking}</think> end."
        result = code_assistant.process_thinking_blocks(content)
        self.assertTrue("<thinking>" in result)
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

    def test_large_response_with_thinking_blocks(self):
        """Test processing an extremely large response with multiple thinking blocks."""
        # Create a very large response with multiple thinking blocks
        normal_text = "This is regular text. " * 500  # 10,000 chars of regular text
        thinking_block1 = "<think>" + ("First thinking block content. " * 1000) + "</think>"  # 28,000+ chars
        thinking_block2 = "<think>" + ("Second thinking block with different content. " * 500) + "</think>"  # 21,500+ chars
        
        # Combine into a response with ~60,000 chars total
        large_response = normal_text + thinking_block1 + "Some text between blocks. " + thinking_block2 + normal_text
        
        # Test with thinking disabled
        code_assistant.SHOW_THINKING = False
        result = code_assistant.process_thinking_blocks(large_response)
        
        # Verify all thinking blocks were removed
        self.assertNotIn("<think>", result)
        self.assertNotIn("</think>", result)
        self.assertNotIn("First thinking block content", result)
        self.assertNotIn("Second thinking block with different content", result)
        
        # Verify normal content is preserved
        self.assertIn("This is regular text", result)
        self.assertIn("Some text between blocks", result)
        
        # Test with thinking enabled
        code_assistant.SHOW_THINKING = True
        result = code_assistant.process_thinking_blocks(large_response)
        
        # Verify thinking blocks are present but truncated
        self.assertIn("<think>", result)
        self.assertIn("</think>", result)
        self.assertIn("[Thinking truncated", result)
        self.assertIn("First thinking block content", result)
        self.assertIn("Second thinking block with different content", result)


if __name__ == '__main__':
    unittest.main() 