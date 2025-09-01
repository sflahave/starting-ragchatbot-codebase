#!/bin/bash

# Run linting checks

echo "🔍 Running flake8 linting..."
uv run flake8 . --show-source --statistics

echo "✅ Linting complete!"