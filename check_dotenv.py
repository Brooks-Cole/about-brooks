#!/usr/bin/env python3
"""
Script to check if python-dotenv is installed properly.
"""

import sys
import importlib.util
import subprocess

def main():
    """Check if python-dotenv is installed and working correctly."""
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    
    # Check if dotenv is installed
    print("\nChecking for dotenv module...")
    is_installed = importlib.util.find_spec("dotenv") is not None
    print(f"Is 'dotenv' module available: {is_installed}")
    
    # Try to install python-dotenv
    print("\nEnsuring python-dotenv is installed...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
        print("Installation command completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Installation command failed: {e}")
    
    # Try to import after installation
    print("\nTrying to import dotenv module...")
    try:
        from dotenv import load_dotenv
        print("Successfully imported dotenv.load_dotenv")
        
        # Try loading a .env file
        print("\nTrying to load a .env file...")
        result = load_dotenv(verbose=True)
        print(f"Result of load_dotenv: {result}")
        
        if result:
            print("Successfully loaded .env file")
        else:
            print("No .env file found or no variables were loaded")
            
            # Check if .env file exists
            import os
            if os.path.exists('.env'):
                print(".env file exists but no variables were loaded")
                # Try to read the file
                with open('.env', 'r') as f:
                    content = f.read()
                    print(f".env file content (first 100 chars): {content[:100]}...")
            else:
                print(".env file does not exist in the current directory")
                print(f"Current directory: {os.getcwd()}")
        
    except ImportError as e:
        print(f"Import failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Show current environment
    print("\nPIP packages:")
    try:
        subprocess.run([sys.executable, "-m", "pip", "list", "--format=columns"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to get pip list: {e}")
        
    # Check sys.path
    print("\nPython sys.path:")
    for path in sys.path:
        print(f"  {path}")

if __name__ == "__main__":
    main()