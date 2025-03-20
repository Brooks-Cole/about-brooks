#!/usr/bin/env python3
"""
Set admin password for aboutBrooks dashboard.
This script updates the .env file with a secure admin password.
"""

import os
import secrets
import string
import sys
from pathlib import Path

def set_admin_password():
    """Set or update the admin password in the .env file"""
    # Find .env file
    env_file = Path('.env')
    
    if not env_file.exists():
        print("Error: .env file not found. Please create a .env file first.")
        return False
    
    # Read current .env content
    with open(env_file, 'r') as f:
        env_content = f.read()
    
    # Check if password already exists
    has_password = 'ADMIN_PASSWORD=' in env_content
    
    # Ask for confirmation if password exists
    if has_password and not force_mode:
        confirm = input("Admin password already exists. Do you want to replace it? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return False
    
    # Ask for custom password or generate one
    if custom_password:
        password = custom_password
    else:
        use_custom = input("Do you want to set a custom password? (y/n): ")
        if use_custom.lower() == 'y':
            password = input("Enter your custom admin password: ")
            if not password:
                print("Error: Password cannot be empty.")
                return False
        else:
            # Generate a secure random password
            chars = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(secrets.choice(chars) for _ in range(16))
    
    # Update or add password in .env file
    if has_password:
        # Replace existing password
        lines = env_content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith('ADMIN_PASSWORD='):
                new_lines.append(f'ADMIN_PASSWORD={password}')
            else:
                new_lines.append(line)
        
        new_env_content = '\n'.join(new_lines)
    else:
        # Add password to end of file
        # Make sure the file ends with a newline
        if env_content and not env_content.endswith('\n'):
            env_content += '\n'
        
        new_env_content = env_content + f'ADMIN_PASSWORD={password}\n'
    
    # Write updated content back to .env file
    with open(env_file, 'w') as f:
        f.write(new_env_content)
    
    # Show success message
    if custom_password:
        print(f"Admin password has been set successfully.")
    else:
        print(f"Admin password has been set successfully. Your new password is:")
        print(f"\n    {password}\n")
        print("Please save this password in a secure location.")
    
    return True

if __name__ == "__main__":
    print("\n🔐 Set Admin Password for aboutBrooks Dashboard 🔐\n")
    
    # Parse command line arguments
    force_mode = False
    custom_password = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--force":
            force_mode = True
        else:
            custom_password = sys.argv[1]
    
    # Run the function
    if set_admin_password():
        print("\n✅ Admin password updated successfully!")
    else:
        print("\n❌ Failed to update admin password.")
        sys.exit(1)