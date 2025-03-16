#!/usr/bin/env python3
"""
Script to fix linting errors in the aboutBrooks project.
Automatically formats Python files to comply with PEP 8.
"""

import os
import subprocess
from pathlib import Path


def run_autopep8(file_path):
    """Run autopep8 on a file to fix formatting issues."""
    print(f"Fixing {file_path}...")
    try:
        # Run autopep8 with aggressive formatting (level 2)
        result = subprocess.run(
            [
                "python3", "-m", "autopep8",
                "--in-place",
                "--aggressive",
                "--aggressive",
                "--max-line-length=79",
                str(file_path)
            ],
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"  Output: {result.stdout}")
        if result.stderr:
            print(f"  Error: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error fixing {file_path}: {e}")
        if e.stdout:
            print(f"  Output: {e.stdout}")
        if e.stderr:
            print(f"  Error: {e.stderr}")
        return False


def fix_undefined_filename_issues(file_path):
    """Fix the undefined 'filename' variable in system_prompt.py"""
    if 'system_prompt.py' not in str(file_path):
        return

    print(f"Fixing undefined 'filename' variable in {file_path}...")
    with open(file_path, 'r') as file:
        content = file.read()

    # Replace {{filename}} with {filename} to avoid F821 undefined name errors
    content = content.replace("{{filename}}", "{filename}")
    # Make sure F-strings with filename are properly formatted
    content = content.replace(
        "'You can see a photo of it here: /static/images/{filename}'",
        "'You can see a photo of it here: /static/images/{filename}'")

    with open(file_path, 'w') as file:
        file.write(content)


def get_python_files(root_dir):
    """Get all Python files in the project."""
    python_files = []
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)
    return python_files


def main():
    """Main function to fix linting issues."""
    # Get the project root directory
    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")

    # Get all Python files
    python_files = get_python_files(project_root)
    print(f"Found {len(python_files)} Python files")

    # Install required packages
    print("Installing required packages...")
    subprocess.run(["python3", "-m", "pip", "install",
                   "--quiet", "autopep8", "flake8"], check=True)

    # First, fix undefined variable issues
    for file_path in python_files:
        fix_undefined_filename_issues(file_path)

    # Then, fix formatting issues
    for file_path in python_files:
        run_autopep8(file_path)

    # Finally, check if there are any remaining issues
    print("\nChecking for remaining issues...")
    try:
        result = subprocess.run(
            ["python3", "-m", "flake8", "--count", "."],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root
        )

        if result.returncode == 0:
            print("✨ All linting errors fixed! ✨")
        else:
            remaining_count = result.stdout.strip().split('\n')[-1]
            print(f"⚠️ {remaining_count} linting errors still remain.")
            print("Some errors may require manual fixes:")
            print(result.stdout)
            print(
                "\nRun 'python -m flake8 <file>' on specific files to see detailed errors.")
    except subprocess.SubprocessError as e:
        print(f"Error checking for remaining issues: {e}")


if __name__ == "__main__":
    main()
