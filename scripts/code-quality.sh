#!/bin/bash

# Code Quality Script
# This script runs the same quality checks as our GitHub Actions workflow
# to ensure consistency between local development and CI/CD

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
CHECK_FORMATTING=true
CHECK_IMPORTS=true
CHECK_LINTING=true
CHECK_TYPES=false
CHECK_COMPLEXITY=false
FIX_MODE=false

# Help function
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --formatting, -f     Run Black formatting checks (default: true)"
    echo "  --imports, -i        Run isort import sorting checks (default: true)"
    echo "  --linting, -l        Run flake8 linting checks (default: true)"
    echo "  --types, -t          Run mypy type checking (default: false)"
    echo "  --complexity, -c     Run pylint complexity analysis (default: false)"
    echo "  --fix                Auto-fix issues where possible (black + isort)"
    echo "  --all                Run all checks including types and complexity"
    echo "  --help, -h           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                   # Run default checks (formatting, imports, linting)"
    echo "  $0 --all             # Run all available checks"
    echo "  $0 --fix             # Auto-fix formatting and import issues"
    echo "  $0 --types           # Run only type checking"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --formatting|-f)
            CHECK_FORMATTING=true
            CHECK_IMPORTS=false
            CHECK_LINTING=false
            shift
            ;;
        --imports|-i)
            CHECK_FORMATTING=false
            CHECK_IMPORTS=true
            CHECK_LINTING=false
            shift
            ;;
        --linting|-l)
            CHECK_FORMATTING=false
            CHECK_IMPORTS=false
            CHECK_LINTING=true
            shift
            ;;
        --types|-t)
            CHECK_FORMATTING=false
            CHECK_IMPORTS=false
            CHECK_LINTING=false
            CHECK_TYPES=true
            shift
            ;;
        --complexity|-c)
            CHECK_FORMATTING=false
            CHECK_IMPORTS=false
            CHECK_LINTING=false
            CHECK_COMPLEXITY=true
            shift
            ;;
        --fix)
            FIX_MODE=true
            shift
            ;;
        --all)
            CHECK_FORMATTING=true
            CHECK_IMPORTS=true
            CHECK_LINTING=true
            CHECK_TYPES=true
            CHECK_COMPLEXITY=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Function to run a check with proper formatting
run_check() {
    local name="$1"
    local command="$2"
    local continue_on_error="$3"

    echo -e "${BLUE}Running $name...${NC}"

    if [[ "$continue_on_error" == "true" ]]; then
        if eval "$command"; then
            echo -e "${GREEN}✓ $name passed${NC}"
        else
            echo -e "${YELLOW}⚠ $name completed with warnings${NC}"
        fi
    else
        if eval "$command"; then
            echo -e "${GREEN}✓ $name passed${NC}"
        else
            echo -e "${RED}✗ $name failed${NC}"
            return 1
        fi
    fi
    echo ""
}

# Ensure we're in a Python environment with the required tools
echo -e "${BLUE}Checking Python environment...${NC}"
for tool in black isort flake8 mypy pylint; do
    if ! command -v "$tool" &> /dev/null; then
        echo -e "${RED}Error: $tool is not installed or not in PATH${NC}"
        echo "Please install the required tools: pip install flake8 black isort mypy pylint"
        exit 1
    fi
done
echo -e "${GREEN}✓ All required tools are available${NC}"
echo ""

# Run checks based on options
exit_code=0

if [[ "$CHECK_FORMATTING" == "true" ]]; then
    if [[ "$FIX_MODE" == "true" ]]; then
        run_check "Black formatting (auto-fix)" "black ." || exit_code=1
    else
        run_check "Black formatting check" "black --check --diff ." || exit_code=1
    fi
fi

if [[ "$CHECK_IMPORTS" == "true" ]]; then
    if [[ "$FIX_MODE" == "true" ]]; then
        run_check "isort import sorting (auto-fix)" "isort ." || exit_code=1
    else
        run_check "isort import sorting check" "isort --check-only --diff ." || exit_code=1
    fi
fi

if [[ "$CHECK_LINTING" == "true" ]]; then
    run_check "flake8 linting" "flake8 --config=config/.flake8 ." || exit_code=1
fi

if [[ "$CHECK_TYPES" == "true" ]]; then
    run_check "MyPy type checking" "mypy . || echo 'Type checking completed with warnings'" "true"
fi

if [[ "$CHECK_COMPLEXITY" == "true" ]]; then
    complexity_cmd="find . -name '*.py' -not -path './.git/*' -not -path './venv/*' | head -20 | xargs pylint --disable=all --enable=complexity || echo 'Complexity analysis completed with warnings'"
    run_check "Pylint complexity analysis" "$complexity_cmd" "true"
fi

if [[ $exit_code -eq 0 ]]; then
    echo -e "${GREEN}All code quality checks passed! 🎉${NC}"
else
    echo -e "${RED}Some code quality checks failed. Please fix the issues above.${NC}"
fi

exit $exit_code
