#!/bin/bash
# Test runner script for repo-to-pdf

set -e  # Exit on error

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Running repo-to-pdf tests...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install test dependencies
echo -e "${GREEN}Installing test dependencies...${NC}"
pip install -q -r requirements.txt

# Run unit tests
echo -e "${GREEN}Running unit tests...${NC}"
python -m pytest tests/test_repo_to_pdf.py -v -m "not integration"

# Run integration tests
echo -e "${GREEN}Running integration tests...${NC}"
python -m pytest tests/test_integration.py -v -m "not slow"

# Run all tests with coverage
echo -e "${GREEN}Running all tests with coverage...${NC}"
python -m pytest

# Check code style (optional)
if command -v flake8 &> /dev/null; then
    echo -e "${GREEN}Checking code style...${NC}"
    flake8 repo-to-pdf.py --max-line-length=100 --ignore=E501,W503
fi

# Generate coverage report
echo -e "${GREEN}Coverage report:${NC}"
coverage report

echo -e "${GREEN}All tests completed!${NC}"
echo -e "HTML coverage report available at: htmlcov/index.html"