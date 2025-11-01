#!/bin/bash
# Run all quality checks

echo "=== Running Code Quality Checks ==="
echo ""

echo "1. Checking code formatting..."
./scripts/check-format.sh
FORMAT_EXIT=$?

echo ""
echo "2. Running linter..."
./scripts/lint.sh
LINT_EXIT=$?

echo ""
echo "3. Running tests..."
uv run pytest
TEST_EXIT=$?

echo ""
echo "=== Quality Check Summary ==="
if [ $FORMAT_EXIT -eq 0 ] && [ $LINT_EXIT -eq 0 ] && [ $TEST_EXIT -eq 0 ]; then
    echo "✓ All checks passed!"
    exit 0
else
    echo "✗ Some checks failed:"
    [ $FORMAT_EXIT -ne 0 ] && echo "  - Format check failed"
    [ $LINT_EXIT -ne 0 ] && echo "  - Linter failed"
    [ $TEST_EXIT -ne 0 ] && echo "  - Tests failed"
    exit 1
fi
