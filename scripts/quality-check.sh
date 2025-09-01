#!/bin/bash

# Run all code quality checks

set -e  # Exit on any error

echo "🧹 Starting code quality checks..."
echo ""

echo "1. Checking code formatting..."
uv run black --check --diff .
if [ $? -eq 0 ]; then
    echo "✅ Code formatting is correct"
else
    echo "❌ Code formatting issues found. Run 'scripts/format.sh' to fix."
    exit 1
fi

echo ""
echo "2. Checking import organization..."
uv run isort --check-only --diff .
if [ $? -eq 0 ]; then
    echo "✅ Import organization is correct"
else
    echo "❌ Import organization issues found. Run 'scripts/format.sh' to fix."
    exit 1
fi

echo ""
echo "3. Running linting checks..."
uv run flake8 . --show-source --statistics
if [ $? -eq 0 ]; then
    echo "✅ No linting issues found"
else
    echo "❌ Linting issues found. Please fix the issues above."
    exit 1
fi

echo ""
echo "4. Running tests..."
uv run pytest
if [ $? -eq 0 ]; then
    echo "✅ All tests passed"
else
    echo "❌ Some tests failed. Please fix the failing tests."
    exit 1
fi

echo ""
echo "🎉 All quality checks passed!"