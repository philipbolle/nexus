#!/bin/bash
# Test runner script for NEXUS pytest suite

set -e

echo "Running NEXUS test suite..."

# Change to project directory
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please set up the project first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Run pytest with coverage
echo "Running unit tests for agent framework..."
python -m pytest tests/unit/agents/ -v --cov=app.agents --cov-report=term-missing

echo "Running unit tests for swarm components..."
python -m pytest tests/unit/swarm/ -v --cov=app.agents.swarm --cov-report=term-missing

echo "Running API tests..."
python -m pytest tests/api/ -v --cov=app.routers --cov-report=term-missing

echo "Running all tests with coverage report..."
python -m pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html:coverage_report

echo "Test suite completed successfully!"
echo "Coverage report available at: coverage_report/index.html"