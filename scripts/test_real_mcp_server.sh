#!/bin/bash
# Script to test Jira Creation Agent with real MCP server
#
# Prerequisites:
# 1. MCP server must be running (see instructions below)
# 2. .env file must contain valid Jira credentials
#
# To start MCP server:
#   cd mcp-atlassian
#   python -m mcp_atlassian --transport streamable-http --port 9000 --path /mcp -vv
#
# Or using Docker:
#   docker run --rm -p 9000:9000 --env-file .env \
#     ghcr.io/sooperset/mcp-atlassian:latest \
#     --transport streamable-http --port 9000 --path /mcp -vv
#
# Required .env variables:
#   JIRA__SERVER_URL=http://localhost:9000/mcp
#   JIRA__PROJECT_KEY=YOUR_PROJECT_KEY
#   JIRA_URL=https://your-domain.atlassian.net
#   JIRA_USERNAME=your-email@example.com
#   JIRA_TOKEN=your-api-token

set -e

echo "=========================================="
echo "Testing Jira Creation Agent with Real MCP Server"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please create .env file with required Jira credentials."
    exit 1
fi

# Check if MCP server URL is configured
if ! grep -q "JIRA__SERVER_URL" .env; then
    echo "WARNING: JIRA__SERVER_URL not found in .env"
    echo "Please add: JIRA__SERVER_URL=http://localhost:9000/mcp"
fi

# Check if project key is configured
if ! grep -q "JIRA__PROJECT_KEY" .env; then
    echo "WARNING: JIRA__PROJECT_KEY not found in .env"
    echo "Please add: JIRA__PROJECT_KEY=YOUR_PROJECT_KEY"
fi

echo "Running tests with REAL_MCP_SERVER=true..."
echo ""

# Activate virtual environment if it exists
if [ -d .venv ]; then
    source .venv/bin/activate
fi

# Run tests with REAL_MCP_SERVER environment variable
REAL_MCP_SERVER=true python -m pytest tests/test_jira_real_mcp_server.py -v -s

echo ""
echo "=========================================="
echo "Tests completed!"
echo "=========================================="

