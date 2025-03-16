#!/usr/bin/env python3
"""
A simple script to test the Anthropic API key.
Run this script to verify that your API key is working correctly.
"""

import os
import anthropic
from dotenv import load_dotenv
import sys


def test_api():
    print("Testing Anthropic API key...")

    # Try to load from .env file
    load_dotenv()

    # Get API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')

    # Manual check if environment variable is not set
    if not api_key:
        try:
            with open('.env', 'r') as f:
                content = f.read()
                import re
                match = re.search(
                    r'ANTHROPIC_API_KEY\s*=\s*[\'"]?(sk-[^\'"]+)', content)
                if match:
                    api_key = match.group(1)
                    print("Retrieved API key directly from .env file")
        except Exception as e:
            print(f"Failed to retrieve API key from .env file: {str(e)}")

    if not api_key:
        print("ERROR: No API key found. Please set the ANTHROPIC_API_KEY environment variable or add it to a .env file.")
        return False

    print(f"Found API key: {api_key[:8]}...{api_key[-4:]}")

    # Test the API key
    try:
        client = anthropic.Anthropic(api_key=api_key)
        print("Successfully initialized Anthropic client")

        # List models
        print("Fetching available models...")
        models = client.models.list()
        print(f"Available models: {[model.id for model in models.data]}")

        # Test a simple message
        print("\nSending a test message...")
        response = client.messages.create(
            model="claude-3-sonnet-20240229",
            system="You are a helpful assistant. Respond with a very short answer.",
            messages=[{"role": "user", "content": "Say hello in a single word"}],
            max_tokens=10
        )

        print(f"Response: {response.content[0].text}")
        print("\nAPI test completed successfully! ✅")
        return True

    except Exception as e:
        print(f"ERROR: API test failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
