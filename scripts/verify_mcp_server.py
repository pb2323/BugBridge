#!/usr/bin/env python3
"""
Quick verification script to check if MCP server is accessible and configured correctly.

Usage:
    python scripts/verify_mcp_server.py

This script checks:
1. MCP server URL is configured
2. MCP server is accessible
3. Jira project key is configured
4. Basic connection can be established
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from bugbridge.config import get_settings
from bugbridge.integrations.mcp_jira import MCPJiraClient, MCPJiraError
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


async def verify_mcp_server():
    """Verify MCP server is accessible and configured correctly."""
    print("=" * 60)
    print("MCP Server Verification")
    print("=" * 60)
    print()

    try:
        # Load settings
        settings = get_settings()
        jira_settings = settings.jira

        # Check server URL
        server_url = str(jira_settings.server_url)
        print(f"✓ MCP Server URL: {server_url}")

        # Check project key
        project_key = jira_settings.project_key
        print(f"✓ Jira Project Key: {project_key}")
        print()

        # Test connection
        print("Testing connection to MCP server...")
        client = MCPJiraClient(
            server_url=server_url,
            project_key=project_key,
            auto_connect=False,
        )

        try:
            await client.connect()
            print("✓ Successfully connected to MCP server")
        except Exception as e:
            print(f"✗ Failed to connect to MCP server: {e}")
            print()
            print("Troubleshooting:")
            print(f"  1. Ensure MCP server is running at {server_url}")
            print("  2. Check server logs for errors")
            print("  3. Verify network connectivity")
            return False

        # Test a simple query
        print("Testing Jira query...")
        try:
            async with client.connection():
                jql = f"project = {project_key} ORDER BY created DESC"
                issues = await client.search_issues(jql, limit=1)
                print(f"✓ Successfully queried Jira project {project_key}")
                if issues:
                    print(f"  Found {len(issues)} recent issue(s)")
                else:
                    print("  No issues found (project may be empty)")
        except Exception as e:
            print(f"✗ Failed to query Jira: {e}")
            print()
            print("Troubleshooting:")
            print(f"  1. Verify project key '{project_key}' exists in Jira")
            print("  2. Check Jira credentials in .env file")
            print("  3. Ensure user has permission to access the project")
            await client.disconnect()
            return False

        await client.disconnect()
        print()
        print("=" * 60)
        print("✓ All checks passed! MCP server is ready for testing.")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"✗ Configuration error: {e}")
        print()
        print("Troubleshooting:")
        print("  1. Check .env file exists and contains required variables:")
        print("     - JIRA__SERVER_URL=http://localhost:9000/mcp")
        print("     - JIRA__PROJECT_KEY=YOUR_PROJECT_KEY")
        print("     - JIRA_URL=https://your-domain.atlassian.net")
        print("     - JIRA_USERNAME=your-email@example.com")
        print("     - JIRA_TOKEN=your-api-token")
        return False


if __name__ == "__main__":
    success = asyncio.run(verify_mcp_server())
    sys.exit(0 if success else 1)

