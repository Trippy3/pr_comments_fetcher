#!/bin/bash
# Simple test runner script

echo "=== Running pytest unit tests ==="
echo ""
echo "Note: This script demonstrates how to run tests."
echo "First, ensure test dependencies are installed:"
echo "  uv sync --all-extras"
echo ""
echo "Example test commands:"
echo "  uv run pytest                              # Run all tests"
echo "  uv run pytest -v                           # Verbose output"
echo "  uv run pytest --cov                        # With coverage"
echo "  uv run pytest src/tests/unit/test_github_review_comments_fetcher.py  # Specific file"
echo ""
echo "To run tests now, execute one of the commands above."
