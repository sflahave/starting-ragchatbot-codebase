#!/bin/bash

# Format code with black and organize imports with isort

echo "🔧 Formatting code with black..."
uv run black .

echo "📚 Organizing imports with isort..."
uv run isort .

echo "✅ Code formatting complete!"