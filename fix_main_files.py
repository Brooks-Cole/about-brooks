#!/usr/bin/env python3
"""
Script to fix linting errors in the main Python files of the aboutBrooks project.
Automatically formats Python files to comply with PEP 8.
"""

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

    # Use double curly braces to escape the curly braces in f-strings
    # that are meant to be preserved for future formatting, not immediate
    content = content.replace(
        "'You can see a photo of it here: /static/images/{filename}'",
        "'You can see a photo of it here: /static/images/{{filename}}'")
    
    content = content.replace(
        "If relevant, include a photo link by saying: 'You can see a photo of it here: /static/images/{filename}'",
        "If relevant, include a photo link by saying: 'You can see a photo of it here: /static/images/{{filename}}'")

    with open(file_path, 'w') as file:
        file.write(content)


def main():
    """Main function to fix linting issues."""
    # Get the project root directory
    project_root = Path(__file__).parent
    print(f"Project root: {project_root}")

    # Define the project's main Python files
    main_files = [
        project_root / "app.py",
        project_root / "improved_photo_database_generator.py",
        project_root / "test_api.py",
        project_root / "wsgi.py",
        project_root / "utils" / "personal_profile.py",
        project_root / "utils" / "photo_database.py",
        project_root / "prompts" / "system_prompt.py",
    ]

    # Filter out files that don't exist
    main_files = [f for f in main_files if f.exists()]
    print(f"Found {len(main_files)} main Python files to fix")

    # Install required packages
    print("Installing required packages...")
    subprocess.run(
        ["python3", "-m", "pip", "install", "--quiet", "autopep8", "flake8"],
        check=True)

    # First, fix undefined variable issues in system_prompt.py
    for file_path in main_files:
        fix_undefined_filename_issues(file_path)

    # Then, fix formatting issues in all main files
    for file_path in main_files:
        run_autopep8(file_path)

    # Finally, check if there are any remaining issues
    print("\nChecking for remaining issues...")
    try:
        # Only check main app files and directories
        result = subprocess.run(
            ["python3", "-m", "flake8", "app.py", "utils", "prompts"],
            check=False,
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            print("✨ All linting errors fixed! ✨")
        else:
            error_lines = result.stdout.strip().split('\n')
            if error_lines and error_lines[-1].isdigit():
                remaining_count = error_lines[-1]
                print(f"⚠️ {remaining_count} linting errors still remain.")
            else:
                print("⚠️ Some linting errors still remain.")
                
            print("Some errors may require manual fixes:")
            print(result.stdout[:500] + "..." if len(result.stdout) > 500 else result.stdout)
            print("\nRun 'python -m flake8 <file>' on specific files to see detailed errors.")
    except subprocess.SubprocessError as e:
        print(f"Error checking for remaining issues: {e}")


if __name__ == "__main__":
    main()