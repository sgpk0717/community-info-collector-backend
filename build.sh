#!/bin/bash
set -e

echo "🚀 Starting build process..."

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies with no cache to avoid permission issues
pip install --no-cache-dir -r requirements.txt

echo "✅ Build completed successfully!"