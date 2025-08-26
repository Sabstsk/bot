#!/usr/bin/env python3
"""
Deployment verification script to check if the bot code is correct
Run this before deploying to Railway to ensure no @check_auth decorators exist
"""

import re

def check_bot_file():
    """Check bot.py for deployment issues"""
    issues = []
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        # Check for @check_auth decorators
        for i, line in enumerate(lines, 1):
            if '@check_auth' in line:
                issues.append(f"Line {i}: Found @check_auth decorator - this will cause NameError")
        
        # Check if check_auth function is defined
        if 'def check_auth(' in content:
            print("✅ check_auth function is defined")
        else:
            issues.append("check_auth function is not defined")
        
        # Check if AUTH_PASSWORD uses environment variable
        if 'os.environ.get(\'AUTH_PASSWORD\'' in content:
            print("✅ AUTH_PASSWORD uses environment variable")
        else:
            issues.append("AUTH_PASSWORD should use environment variable")
        
        # Check for manual auth checks
        manual_auth_count = content.count('if user_id not in AUTHORIZED_USERS:')
        print(f"✅ Found {manual_auth_count} manual authentication checks")
        
        if issues:
            print("\n❌ DEPLOYMENT ISSUES FOUND:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("\n🎉 Bot is ready for Railway deployment!")
            return True
            
    except FileNotFoundError:
        print("❌ bot.py file not found")
        return False
    except Exception as e:
        print(f"❌ Error checking file: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Checking bot.py for deployment readiness...")
    check_bot_file()
