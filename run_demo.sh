#!/bin/bash
# Agent-402 One-Command Demo Script
# Per PRD Section 10: One-command demo run
# Issue #76: Create complete demo execution script

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_PORT=8000
HEALTH_URL="http://localhost:${BACKEND_PORT}/health"
MAX_HEALTH_CHECKS=30
HEALTH_CHECK_INTERVAL=2

# Project paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="${SCRIPT_DIR}/backend"
RUN_CREW_SCRIPT="${BACKEND_DIR}/run_crew.py"

# Demo identifiers
PROJECT_ID="proj_demo_$(date +%Y%m%d)"
RUN_ID="demo-run-$(date +%Y%m%d-%H%M%S)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}🚀 Starting Agent-402 Demo${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Project ID: ${PROJECT_ID}"
echo "Run ID: ${RUN_ID}"
echo "Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S UTC")"
echo ""

# Function to check if backend is running
check_backend_health() {
    curl -s -f "${HEALTH_URL}" > /dev/null 2>&1
    return $?
}

# Function to start backend server
start_backend() {
    echo -e "${YELLOW}Starting backend server...${NC}"

    # Check if backend is already running
    if check_backend_health; then
        echo -e "${GREEN}✓ Backend server is already running${NC}"
        return 0
    fi

    # Check if .env file exists
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        echo -e "${RED}✗ Error: .env file not found${NC}"
        echo "Please create .env file with required configuration:"
        echo "  - API_KEY=your_zerodb_api_key"
        echo "  - BASE_URL=https://api.ainative.studio/v1/public"
        echo "  - PROJECT_ID=your_project_id"
        exit 1
    fi

    # Detect Python command
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}✗ Error: Python not found${NC}"
        return 1
    fi

    # Start backend in background
    cd "${BACKEND_DIR}"
    echo "Starting uvicorn server on port ${BACKEND_PORT}..."
    nohup ${PYTHON_CMD} -m uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} > /dev/null 2>&1 &
    BACKEND_PID=$!

    # Wait for health check
    echo "Waiting for backend to be healthy..."
    for i in $(seq 1 ${MAX_HEALTH_CHECKS}); do
        if check_backend_health; then
            echo -e "${GREEN}✓ Backend server is healthy (${i}/${MAX_HEALTH_CHECKS})${NC}"
            cd "${SCRIPT_DIR}"
            return 0
        fi
        echo -n "."
        sleep ${HEALTH_CHECK_INTERVAL}
    done

    echo -e "${RED}✗ Backend server failed to start after ${MAX_HEALTH_CHECKS} attempts${NC}"
    cd "${SCRIPT_DIR}"
    exit 1
}

# Function to execute CrewAI workflow
execute_crew_workflow() {
    echo ""
    echo -e "${YELLOW}Executing CrewAI workflow...${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""

    cd "${BACKEND_DIR}"

    # Detect Python command (python3 or python)
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}✗ Error: Python not found${NC}"
        cd "${SCRIPT_DIR}"
        return 1
    fi

    # Execute crew with demo parameters
    ${PYTHON_CMD} run_crew.py \
        --project-id "${PROJECT_ID}" \
        --run-id "${RUN_ID}" \
        --verbose

    CREW_EXIT_CODE=$?
    cd "${SCRIPT_DIR}"

    return ${CREW_EXIT_CODE}
}

# Main execution flow
main() {
    START_TIME=$(date +%s)

    # Start backend server
    start_backend

    # Execute CrewAI workflow
    if execute_crew_workflow; then
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${GREEN}✅ Demo Complete!${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""

        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        echo "Run ID: ${RUN_ID}"
        echo "Duration: ${DURATION} seconds"
        echo ""
        echo "View results at: http://localhost:3000"
        echo "API documentation: http://localhost:${BACKEND_PORT}/docs"
        echo ""

        exit 0
    else
        echo ""
        echo -e "${RED}✗ Demo failed with errors${NC}"
        echo ""
        echo "Check logs for details:"
        echo "  - Backend log: ${BACKEND_DIR}/backend.log"
        echo "  - Crew log: ${BACKEND_DIR}/crew_execution.log"
        echo ""

        exit 1
    fi
}

# Trap errors and cleanup
trap 'echo -e "${RED}✗ Demo execution interrupted${NC}"; exit 1' INT TERM

# Run main function
main
