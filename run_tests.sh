#!/bin/bash
# ROXY Test Runner
# Runs all tests with coverage reporting

set -e

cd "$(dirname "$0")"

echo "======================================"
echo "ROXY Test Suite"
echo "======================================"
echo ""

# Check if pytest is installed
if ! python3 -m pytest --version > /dev/null 2>&1; then
    echo "Installing test dependencies..."
    pip install -q pytest pytest-cov pytest-asyncio requests-mock
fi

# Check if prometheus_client is installed
if ! python3 -c "import prometheus_client" > /dev/null 2>&1; then
    echo "Installing prometheus_client for metrics..."
    pip install -q prometheus_client
fi

echo "Running tests..."
echo ""

# Run tests with coverage
python3 -m pytest tests/ \
    --cov=. \
    --cov-report=term-missing \
    --cov-report=html:htmlcov \
    --cov-config=.coveragerc \
    -v \
    --tb=short \
    "$@"

EXIT_CODE=$?

echo ""
echo "======================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed (exit code: $EXIT_CODE)"
fi
echo "======================================"
echo ""
echo "Coverage report: htmlcov/index.html"

exit $EXIT_CODE
