import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add current directory to path so we can import main
sys.path.append(os.getcwd())

# Mock the Groq client before importing main to avoid API key errors during import if we were initializing at module level with strict checks
# (Our main.py logic handles missing key gracefully, but good to be safe)
with patch.dict(os.environ, {"GROQ_API_KEY": "fake_key"}):
    import main

class TestHoneypot(unittest.TestCase):
    def setUp(self):
        # Mock the groq client in main
        self.mock_completion = MagicMock()
        self.mock_completion.choices = [MagicMock(message=MagicMock(content="I am a confused victim."))]
        
        self.mock_client = MagicMock()
        self.mock_client.chat.completions.create.return_value = self.mock_completion
        
        main.groq_client = self.mock_client

    def test_intelligence_extraction(self):
        print("\nTesting Intelligence Extraction...")
        intel = main.Intelligence()
        text = "Pay to my UPI scammer@okicici immediately."
        main.extract_intelligence(text, intel)
        
        self.assertIn("scammer@okicici", intel.upiIds)
        self.assertIn("pay", intel.suspiciousKeywords)
        self.assertTrue(intel.scamDetected)
        print("✅ Intelligence Extraction Passed")

    def test_ai_reply_generation(self):
        print("\nTesting AI Reply Generation...")
        reply = main.generate_ai_reply("Hello")
        
        # Check if the mock was called
        self.mock_client.chat.completions.create.assert_called_once()
        self.assertEqual(reply, "I am a confused victim.")
        print("✅ AI Reply Generation Passed")

if __name__ == '__main__':
    unittest.main()
