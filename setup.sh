#!/bin/bash
# Setup script for Azure Custom Role Designer

set -e

echo "=== Azure Custom Role Designer Setup ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not installed."
    exit 1
fi

echo "✓ Python $(python3 --version) found"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

echo "✓ Virtual environment ready"

# Activate virtual environment
source venv/bin/activate

echo ""
echo "Installing Azure Custom Role Designer package..."
pip install --upgrade pip setuptools wheel
pip install -e .
echo "✓ Package installed successfully"

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo ""
    echo "⚠ Azure CLI not found. Installing..."
    curl -sL https://aka.ms/InstallAzureCLIDeb | bash
fi

echo "✓ Azure CLI ready"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Login to Azure: az login"
echo "3. Run the tool: custom-role-designer"
echo "4. Check the guide: PLATFORM_ENGINEER_GUIDE.md"
echo ""
echo "For help: custom-role-designer --help"
