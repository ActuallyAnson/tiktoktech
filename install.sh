#!/bin/bash
# Quick installation script for TikTok Compliance Classifier

echo "🚀 Installing TikTok Compliance Classifier..."

# Check if Python 3.11+ is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.11+ first."
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python $python_version detected. Requires Python 3.11+."
    exit 1
fi

echo "✅ Python $python_version - Compatible"

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    echo "📋 Creating .env file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your API keys!"
else
    echo "✅ .env file already exists"
fi

# Run verification
echo "🔍 Running installation verification..."
python3 verify_installation.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Installation complete!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env with your Gemini API key"
    echo "2. For Slack integration, follow SLACK_SETUP.md"
    echo "3. Test with: python3 batch_classifier.py"
else
    echo "❌ Installation verification failed. Please check the errors above."
    exit 1
fi
