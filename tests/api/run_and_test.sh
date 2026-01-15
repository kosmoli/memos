#!/bin/bash
# Script to start Memos with Docker Compose and run API tests

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Memos Docker Test Runner${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}Error: Docker is not running. Please start Docker and try again.${NC}"
        exit 1
    fi
}

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    docker compose -f test-docker-compose.yml --project-directory "$PROJECT_ROOT" down
    echo -e "${GREEN}Services stopped.${NC}"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Main execution
main() {
    check_docker

    echo -e "${YELLOW}Step 1: Building and starting Memos services...${NC}"
    docker compose -f test-docker-compose.yml --project-directory "$PROJECT_ROOT" up --build -d

    echo ""
    echo -e "${YELLOW}Step 2: Waiting for Memos server to be ready...${NC}"

    # Wait for the server to be healthy
    MAX_WAIT=120
    WAIT_TIME=0
    while [ $WAIT_TIME -lt $MAX_WAIT ]; do
        if curl -s http://localhost:8283/health > /dev/null 2>&1; then
            echo -e "${GREEN}Memos server is ready!${NC}"
            break
        fi
        echo -n "."
        sleep 2
        WAIT_TIME=$((WAIT_TIME + 2))
    done

    if [ $WAIT_TIME -ge $MAX_WAIT ]; then
        echo ""
        echo -e "${RED}Error: Memos server did not become ready within ${MAX_WAIT} seconds${NC}"
        echo -e "${YELLOW}Check logs with: docker compose -f test-docker-compose.yml --project-directory $PROJECT_ROOT logs memos${NC}"
        exit 1
    fi

    echo ""
    echo -e "${YELLOW}Step 3: Running API tests...${NC}"
    echo ""

    # Check if Python 3 is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Error: Python 3 is not installed${NC}"
        exit 1
    fi

    # Check if httpx is installed
    if ! python3 -c "import httpx" 2>/dev/null; then
        echo -e "${YELLOW}Installing httpx...${NC}"
        pip3 install httpx
    fi

    # Run the tests
    python3 test_api_changes.py "$@"

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Test run complete!${NC}"
    echo -e "${GREEN}========================================${NC}"
}

# Run main function
main "$@"
