# Testing with Real MCP Server

This guide explains how to test the Jira Creation Agent with a real MCP server (not mocked responses).

## Prerequisites

1. **MCP Server Running**: The `mcp-atlassian` server must be running and accessible
2. **Jira Credentials**: Valid Jira credentials configured in `.env` file
3. **Jira Project**: Access to a Jira project for creating test tickets

## Setup

### 1. Configure Environment Variables

Add the following to your `.env` file:

```bash
# MCP Server Configuration
JIRA__SERVER_URL=http://localhost:9000/mcp
JIRA__PROJECT_KEY=YOUR_PROJECT_KEY

# Jira API Credentials (for MCP server)
JIRA_URL=https://your-domain.atlassian.net
JIRA_USERNAME=your-email@example.com
JIRA_TOKEN=your-api-token

# Optional: For Jira Server/Data Center
# JIRA_PERSONAL_TOKEN=your-personal-access-token
```

### 2. Start the MCP Server

#### Option A: Using Python (Local)

```bash
cd mcp-atlassian
python -m mcp_atlassian --transport streamable-http --port 9000 --path /mcp -vv
```

#### Option B: Using Docker

```bash
docker run --rm -p 9000:9000 --env-file .env \
  ghcr.io/sooperset/mcp-atlassian:latest \
  --transport streamable-http --port 9000 --path /mcp -vv
```

The server should start and listen on `http://localhost:9000/mcp`.

### 3. Verify MCP Server is Running

Test the connection:

```bash
curl http://localhost:9000/health
```

Should return: `{"status":"ok"}`

## Running Tests

### Run All Real MCP Server Tests

```bash
# Using the provided script
./scripts/test_real_mcp_server.sh

# Or directly with pytest
REAL_MCP_SERVER=true python -m pytest tests/test_jira_real_mcp_server.py -v
```

### Run Specific Tests

```bash
# Test connection only
REAL_MCP_SERVER=true python -m pytest tests/test_jira_real_mcp_server.py::test_mcp_server_connection -v

# Test full end-to-end flow
REAL_MCP_SERVER=true python -m pytest tests/test_jira_real_mcp_server.py::test_jira_creation_with_real_mcp_server -v -s
```

## Test Coverage

The real MCP server tests cover:

1. **Connection Testing**: Verifies connection to MCP server
2. **Project Info Retrieval**: Tests querying Jira project information
3. **End-to-End Flow**: Complete workflow from feedback to Jira ticket creation
4. **Error Handling**: Tests error scenarios (invalid project keys, etc.)
5. **Connection Retry**: Verifies retry logic works correctly

## Important Notes

### Test Ticket Cleanup

Test tickets created during testing are **not automatically deleted**. You should:

1. Manually delete test tickets in Jira after testing
2. Or use a dedicated test project
3. Or uncomment the cleanup code in `test_jira_creation_with_real_mcp_server`

### Test Isolation

- Tests use a unique post ID (`real_mcp_test`) to avoid conflicts
- Each test run creates a new Jira ticket
- Test tickets are prefixed with `[Bug]` or `[Story]` based on analysis

### Skipping Tests

If `REAL_MCP_SERVER` environment variable is not set, all tests in this file are automatically skipped. This prevents accidental execution in CI/CD pipelines where a real server may not be available.

## Troubleshooting

### Connection Errors

If you see connection errors:

1. **Check MCP server is running**:
   ```bash
   curl http://localhost:9000/health
   ```

2. **Verify server URL in .env**:
   ```bash
   echo $JIRA__SERVER_URL
   # Should be: http://localhost:9000/mcp
   ```

3. **Check server logs** for authentication or configuration errors

### Authentication Errors

If you see authentication errors:

1. Verify Jira credentials in `.env`:
   - `JIRA_URL` should be your Jira instance URL
   - `JIRA_USERNAME` should be your email
   - `JIRA_TOKEN` should be a valid API token

2. For Jira Server/Data Center, use `JIRA_PERSONAL_TOKEN` instead

### Project Key Errors

If you see project key errors:

1. Verify `JIRA__PROJECT_KEY` matches an existing project in your Jira instance
2. Ensure your user has permission to create issues in that project

## Example Test Output

```
tests/test_jira_real_mcp_server.py::test_mcp_server_connection PASSED
tests/test_jira_real_mcp_server.py::test_mcp_server_get_project_info PASSED
tests/test_jira_real_mcp_server.py::test_jira_creation_with_real_mcp_server PASSED
  Successfully created Jira ticket PROJ-123 via real MCP server
  Successfully retrieved ticket PROJ-123 from Jira
tests/test_jira_real_mcp_server.py::test_mcp_server_error_handling PASSED
tests/test_jira_real_mcp_server.py::test_mcp_server_connection_retry PASSED
```

## Next Steps

After verifying tests pass with the real MCP server:

1. Mark task 7.11 as complete
2. Consider adding these tests to CI/CD (with proper environment setup)
3. Document any issues or limitations discovered during testing

