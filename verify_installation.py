#!/usr/bin/env python3
"""
Installation verification script for TikTok Compliance Classifier
Run this script to verify your installation is working correctly.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    version = sys.version_info
    if version.major != 3 or version.minor < 11:
        print(f"❌ Python {version.major}.{version.minor} detected. Requires Python 3.11+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Compatible")
    return True

def check_dependencies():
    """Check if required dependencies are installed."""
    required_packages = [
        'google.generativeai',
        'pandas', 
        'dotenv',
    ]
    
    optional_packages = [
        'slack_bolt',
        'requests'
    ]
    
    print("\n📦 Checking required dependencies:")
    missing_required = []
    for package in required_packages:
        try:
            if package == 'google.generativeai':
                import google.generativeai
            elif package == 'dotenv':
                import dotenv
            else:
                __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - Missing")
            missing_required.append(package)
    
    print("\n📦 Checking optional dependencies (for Slack integration):")
    missing_optional = []
    for package in optional_packages:
        try:
            __import__(package.replace('.', '_'))
            print(f"✅ {package}")
        except ImportError:
            print(f"⚠️  {package} - Missing (optional)")
            missing_optional.append(package)
    
    return missing_required, missing_optional

def check_env_file():
    """Check if .env file exists and has required variables."""
    env_path = Path('.env')
    if not env_path.exists():
        print("\n❌ .env file not found. Copy .env.example to .env and configure your API keys.")
        return False
    
    with open(env_path) as f:
        content = f.read()
    
    required_vars = ['GEMINI_API_KEY']
    optional_vars = ['SLACK_BOT_TOKEN', 'SLACK_APP_TOKEN']
    
    print("\n🔐 Checking environment variables:")
    missing_required = []
    for var in required_vars:
        if var in content and 'your_' not in content.split(f'{var}=')[1].split('\n')[0]:
            print(f"✅ {var} - Configured")
        else:
            print(f"❌ {var} - Not configured")
            missing_required.append(var)
    
    for var in optional_vars:
        if var in content and 'your_' not in content.split(f'{var}=')[1].split('\n')[0]:
            print(f"✅ {var} - Configured")
        else:
            print(f"⚠️  {var} - Not configured (needed for Slack integration)")
    
    return len(missing_required) == 0

def check_data_files():
    """Check if required data files exist."""
    required_files = [
        'data/sample_features.csv',
        'data/terminology.json'
    ]
    
    print("\n📁 Checking data files:")
    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - Missing")
            all_exist = False
    
    return all_exist

def test_basic_functionality():
    """Test basic classifier functionality."""
    print("\n🧪 Testing basic functionality:")
    try:
        from src.processors.gemini_classifier import GeminiClassifier
        print("✅ GeminiClassifier import successful")
        
        # Don't actually call the API in verification
        print("✅ Basic setup appears functional")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Warning: {e}")
        return True  # Non-critical error

def main():
    """Run all verification checks."""
    print("🔍 TikTok Compliance Classifier - Installation Verification\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", lambda: len(check_dependencies()[0]) == 0),
        ("Environment File", check_env_file),
        ("Data Files", check_data_files),
        ("Basic Functionality", test_basic_functionality)
    ]
    
    passed = 0
    total = len(checks)
    
    for name, check_func in checks:
        if check_func():
            passed += 1
    
    print(f"\n📊 Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Installation verified! Your system is ready to use.")
        print("\nNext steps:")
        print("1. Run: python3 batch_classifier.py")
        print("2. For Slack integration: python3 slack_bot.py")
    else:
        print("❌ Some issues found. Please fix the above errors and run verification again.")
        print("\nFor help:")
        print("1. Check README.md for installation instructions")
        print("2. Follow SLACK_SETUP.md for Slack integration")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
