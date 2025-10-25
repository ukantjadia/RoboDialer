#!/bin/bash

# CSV Combination API Processor - Shell Script
# This script runs the combination processor on Linux/Mac systems

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.7"

        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "Python $PYTHON_VERSION found"
            PYTHON_CMD="python3 -u"
            return 0
        else
            print_error "Python version $PYTHON_VERSION is too old. Required: $REQUIRED_VERSION+"
            return 1
        fi
    elif command_exists python; then
        PYTHON_VERSION=$(python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        REQUIRED_VERSION="3.7"

        if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
            print_success "Python $PYTHON_VERSION found"
            PYTHON_CMD="python -u"
            return 0
        else
            print_error "Python version $PYTHON_VERSION is too old. Required: $REQUIRED_VERSION+"
            return 1
        fi
    else
        print_error "Python is not installed or not in PATH"
        return 1
    fi
}

# Function to setup virtual environment
setup_virtual_env() {
    if [ -d ".venv" ]; then
        print_status "Virtual environment found, activating..."
        source .venv/bin/activate
        print_success "Virtual environment activated"
    else
        print_warning "Virtual environment not found"
        print_status "Creating virtual environment..."
        $PYTHON_CMD -m venv .venv
        source .venv/bin/activate
        print_success "Virtual environment created and activated"
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    if [ -f "requirements_combination_processor.txt" ]; then
        pip install -r requirements_combination_processor.txt
        print_success "Dependencies installed"
    else
        print_error "requirements_combination_processor.txt not found"
        exit 1
    fi
}

# Function to check if API server is running
check_api_server() {
    API_URL=$(python -c "
import json
try:
    with open('config_combination_processor.json', 'r') as f:
        config = json.load(f)
    print(config.get('api_settings', {}).get('url', 'https://sandbox-api.saasquatchleads.com/scraper/scrape-stream'))
except:
    print('https://sandbox-api.saasquatchleads.com/scraper/scrape-stream')
")

    print_status "Checking API server at: $API_URL"

    if command_exists curl; then
        if curl -s --connect-timeout 5 "$API_URL" >/dev/null 2>&1; then
            print_success "API server is reachable"
        else
            print_warning "API server might not be running or reachable"
            print_status "Continuing anyway; the processor will log any connection issues"
        fi
    else
        print_warning "curl not found, skipping API server check"
    fi
}

# Show latest output CSVs
show_latest_outputs() {
    print_status "Latest result files:"
    ls -1t results_output_*.csv 2>/dev/null | head -5 || echo "No result files found yet"
}

# Function to run the processor
run_processor() {
    print_status "Starting combination processor..."
    print_status "Press Ctrl+C to stop processing"
    echo

    # Ensure we're in the service directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"

    if [ -f "run_combination_processor.py" ]; then
        $PYTHON_CMD run_combination_processor.py
        echo
        show_latest_outputs
    else
        print_error "run_combination_processor.py not found"
        exit 1
    fi
}

# Function to run setup test
run_setup_test() {
    print_status "Running setup test..."

    if [ -f "test_setup.py" ]; then
        $PYTHON_CMD test_setup.py
        if [ $? -eq 0 ]; then
            print_success "Setup test passed"
        else
            print_error "Setup test failed"
            exit 1
        fi
    else
        print_error "test_setup.py not found"
        exit 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help       Show this help message"
    echo "  -c, --check      Only check dependencies and API server"
    echo "  -i, --install    Install dependencies only"
    echo "  -t, --test       Run setup test to verify everything works"
    echo "  -l, --latest     Show latest generated CSV outputs"
    echo
    echo "Examples:"
    echo "  $0               # Run the processor"
    echo "  $0 --check       # Check setup only"
    echo "  $0 --install     # Install dependencies only"
    echo "  $0 --test        # Run setup test"
    echo "  $0 --latest      # Show latest CSVs"
}

# Main execution
main() {
    echo "========================================"
    echo "CSV Combination API Processor"
    echo "========================================"
    echo

    # Ensure we're in the service directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"
    print_status "Working directory: $(pwd)"

    # Parse command line arguments
    case "${1:-}" in
        -h|--help)
            show_usage
            exit 0
            ;;
        -c|--check)
            print_status "Checking setup only..."
            check_python_version || exit 1
            check_api_server
            print_success "Setup check completed"
            exit 0
            ;;
        -i|--install)
            print_status "Installing dependencies only..."
            check_python_version || exit 1
            setup_virtual_env
            install_dependencies
            print_success "Dependencies installed successfully"
            exit 0
            ;;
        -t|--test)
            print_status "Running setup test..."
            check_python_version || exit 1
            setup_virtual_env
            install_dependencies
            run_setup_test
            print_success "Setup test completed"
            exit 0
            ;;
        -l|--latest)
            show_latest_outputs
            exit 0
            ;;
        "")
            # No arguments, run normally
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac

    # Check Python
    check_python_version || exit 1

    # Setup virtual environment
    setup_virtual_env

    # Install dependencies
    install_dependencies

    # Check API server
    check_api_server

    # Run the processor
    run_processor

    echo
    print_success "Processing completed!"
}

# Trap Ctrl+C and handle gracefully
trap 'echo -e "\n${YELLOW}[WARNING]${NC} Processing interrupted by user"; exit 130' INT

# Run main function
main "$@"