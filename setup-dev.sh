#!/bin/bash
# ROXY Development Environment Setup

set -e

echo "=== ROXY Development Setup ==="
echo ""

# Create virtual environment
if [ ! -d "venv-dev" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv-dev
fi

# Activate virtual environment
source venv-dev/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install development dependencies
echo "Installing development dependencies..."
pip install -r requirements-dev.txt

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

echo ""
echo "✅ Development environment ready!"
echo ""
echo "To activate: source venv-dev/bin/activate"
echo "To run tests: pytest tests/ -v"
echo "To format code: black services/ voice/ agents/"
