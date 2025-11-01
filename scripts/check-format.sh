#!/bin/bash
# Check code formatting without modifying files

echo "Checking isort..."
uv run isort --check-only backend/ main.py

echo "Checking black..."
uv run black --check backend/ main.py

echo "Format check complete!"
