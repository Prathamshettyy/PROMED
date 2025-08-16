#!/usr/bin/env python3
"""
Environment setup script for ProMed PythonAnywhere deployment
Run this script to create your .env file with proper configuration
"""

import os
import secrets
import string

def generate_secret_key(length=50):
    """Generate a secure random secret key"""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(alphabet) for i in range(length))

def create_env_file():
    """Create .env file with PythonAnywhere configuration"""
    
    print("🔧 ProMed PythonAnywhere Environment Setup")
    print("=" * 50)
    print("This script will help you create the .env file for PythonAnywhere deployment.")
    print()
    
    # Get user input with validation
    while True:
        username = input("Enter your PythonAnywhere username: ").strip()
        if username:
            break
        print("❌ Username cannot be empty. Please try again.")
    
    while True:
        mysql_password = input("Enter your MySQL password from PythonAnywhere: ").strip()
        if mysql_password:
            break
        print("❌ MySQL password cannot be empty. Please try again.")
    
    # Secret key generation
    print("\n🔐 Generating secure secret key...")
    secret_key = generate_secret_key()
    
    # Optional email configuration
    print("\n📧 Email Configuration (for expiry alerts):")
    print("Press Enter to skip email configuration for now.")
    mail_username = input("Enter your Gmail address (optional): ").strip()
    mail_password = ""
    
    if mail_username:
        print("📝 Note: You need to use an 'App Password' from Gmail, not your regular password.")
        print("   Go to Gmail Settings > Security > 2-Step Verification > App Passwords")
        mail_password = input("Enter your Gmail app password: ").strip()
    
    # Create .env content
    env_content = f"""# ProMed PythonAnywhere Configuration
# Generated on {os.popen('date').read().strip() if os.name != 'nt' else 'Windows'}

# Security
SECRET_KEY={secret_key}

# MySQL Database Configuration
MYSQL_USERNAME={username}
MYSQL_PASSWORD={mysql_password}
MYSQL_HOST={username}.mysql.pythonanywhere-services.com
MYSQL_DBNAME={username}$promed

# PythonAnywhere Environment Indicator
PYTHONANYWHERE_USERNAME={username}
PYTHONANYWHERE_DOMAIN=pythonanywhere.com

# Email Configuration (for expiry alerts)
MAIL_USERNAME={mail_username}
MAIL_PASSWORD={mail_password}

# Application Settings
FLASK_ENV=production
FLASK_DEBUG=False
"""
    
    # Write to .env file
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("\n✅ .env file created successfully!")
        print(f"📝 File location: {os.path.abspath('.env')}")
        
        # Security reminder
        print("\n🚨 IMPORTANT SECURITY REMINDERS:")
        print("   1. Keep your .env file secure and don't share it publicly")
        print("   2. Don't commit .env to git (it should be in .gitignore)")
        print("   3. Only upload .env to your PythonAnywhere account")
        
        # Show configuration summary
        print("\n📋 Configuration Summary:")
        print(f"   ├── PythonAnywhere Username: {username}")
        print(f"   ├── MySQL Database: {username}$promed")
        print(f"   ├── MySQL Host: {username}.mysql.pythonanywhere-services.com")
        print(f"   ├── Secret Key: ✓ Generated ({len(secret_key)} characters)")
        print(f"   └── Email Alerts: {'✓ Configured' if mail_username else '❌ Skipped'}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error creating .env file: {e}")
        return False

def verify_env_file():
    """Verify the created .env file"""
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        return False
    
    try:
        with open('.env', 'r') as f:
            content = f.read()
        
        required_vars = [
            'SECRET_KEY',
            'MYSQL_USERNAME', 
            'MYSQL_PASSWORD',
            'MYSQL_HOST',
            'MYSQL_DBNAME',
            'PYTHONANYWHERE_USERNAME'
        ]
        
        missing_vars = []
        for var in required_vars:
            if f'{var}=' not in content:
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing required variables: {', '.join(missing_vars)}")
            return False
        
        print("✅ .env file verification passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying .env file: {e}")
        return False

def main():
    """Main function"""
    print("🚀 ProMed Environment Setup Tool")
    print("=" * 40)
    
    # Check if .env already exists
    if os.path.exists('.env'):
        response = input("⚠️  .env file already exists. Overwrite? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print("👋 Setup cancelled. Existing .env file preserved.")
            return
        
        # Backup existing file
        backup_name = '.env.backup'
        os.rename('.env', backup_name)
        print(f"📁 Existing .env backed up as {backup_name}")
    
    # Create new .env file
    success = create_env_file()
    
    if success:
        # Verify the file
        verify_env_file()
        
        print("\n🎉 Environment setup complete!")
        print("\n📝 Next steps:")
        print("   1. Upload this .env file to your PythonAnywhere project directory")
        print("   2. Make sure your MySQL database is created in PythonAnywhere")
        print("   3. Run the database initialization script")
        print("   4. Configure your web app settings")
        
    else:
        print("\n❌ Environment setup failed!")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())