# MCP Atlassian Server Structure Study

This document provides a comprehensive study of the existing `mcp-atlassian` server structure and MCP (Model Context Protocol) protocol to guide the BugBridge Jira integration implementation.

## Table of Contents

1. [MCP Protocol Overview](#mcp-protocol-overview)
2. [Server Architecture](#server-architecture)
3. [Tool Registration System](#tool-registration-system)
4. [Jira Tool Structure](#jira-tool-structure)
5. [Integration Strategy](#integration-strategy)
6. [Key Components](#key-components)

---

## MCP Protocol Overview

### What is MCP?

Model Context Protocol (MCP) is a protocol for connecting AI applications with external tools and data sources. It enables:
- **Tool Discovery**: Servers expose tools that can be called by clients
- **Standardized Communication**: JSON-RPC-like protocol over stdio, HTTP, or WebSocket
- **Type Safety**: Tools have defined schemas for inputs/outputs
- **Authentication**: Support for various auth methods (OAuth, API tokens, etc.)

### MCP Server Types

The `mcp-atlassian` server supports multiple transport methods:
1. **stdio** (default): Standard input/output communication
2. **HTTP/SSE**: Server-Sent Events transport
3. **HTTP/Streamable**: Streamable HTTP transport

### Tool Execution Flow

```
Client (BugBridge) → MCP Server → Tool Handler → Jira API → Response → Client
```

---

## Server Architecture

### Main Server Structure

The server uses **FastMCP** framework for building MCP servers:

```
mcp-atlassian/
├── src/mcp_atlassian/
│   ├── servers/
│   │   ├── main.py          # Main FastMCP server instance
│   │   ├── jira.py          # Jira tool definitions
│   │   ├── confluence.py    # Confluence tool definitions
│   │   ├── context.py       # Application context management
│   │   └── dependencies.py  # Dependency injection
│   ├── jira/
│   │   ├── client.py        # Jira API client wrapper
│   │   ├── issues.py        # Issue operations
│   │   ├── search.py        # Search operations
│   │   └── ...
│   └── models/
│       └── jira/
│           └── issue.py     # Pydantic models for Jira entities
```

### FastMCP Framework

**FastMCP** is a Python framework for building MCP servers:
- Uses decorators to register tools: `@jira_mcp.tool(tags={"jira", "write"})`
- Provides context management through `Context` parameter
- Handles authentication, error handling, and tool filtering
- Supports async/await patterns

### Server Initialization

```python
from fastmcp import FastMCP

# Create server instance
jira_mcp = FastMCP(
    name="Jira MCP Service",
    description="Provides tools for interacting with Atlassian Jira.",
)

# Register tools using decorator
@jira_mcp.tool(tags={"jira", "write"})
async def create_issue(ctx: Context, project_key: str, summary: str, ...):
    # Tool implementation
    pass
```

---

## Tool Registration System

### Tool Decorator

Tools are registered using the `@jira_mcp.tool()` decorator:

```python
@jira_mcp.tool(tags={"jira", "write"})
@check_write_access  # Optional: access control decorator
async def create_issue(
    ctx: Context,
    project_key: Annotated[str, Field(description="...")],
    summary: Annotated[str, Field(description="...")],
    # ... more parameters
) -> str:
    """Tool description"""
    # Implementation
    return json.dumps(result)
```

**Key Aspects:**
- `tags`: Categorize tools (e.g., `{"jira", "write"}` for filtering)
- `Context`: Provides access to dependencies (Jira client, config, etc.)
- `Annotated[Type, Field(...)]`: Pydantic-style field definitions for parameters
- Return type: Usually JSON string or structured data

### Tool Categories

Tools are categorized by tags:
- **Read operations**: `tags={"jira", "read"}`
- **Write operations**: `tags={"jira", "write"}`
- Tools can be filtered by `ENABLED_TOOLS` environment variable
- Write tools are disabled in `READ_ONLY_MODE`

### Context Object

The `Context` parameter provides:
- **Dependencies**: Access to Jira clients, configuration
- **Request context**: Per-request state
- **Lifespan context**: Application-level state

```python
async def create_issue(ctx: Context, ...):
    jira = await get_jira_fetcher(ctx)  # Get Jira client from context
    # Use jira client...
```

---

## Jira Tool Structure

### Available Jira Tools

The server provides numerous Jira tools that we can leverage:

#### Read Operations
- `jira_get_issue`: Get issue details
- `jira_search`: Search issues using JQL
- `jira_get_all_projects`: List all projects
- `jira_get_project_issues`: Get issues for a project
- `jira_get_transitions`: Get available status transitions
- `jira_get_worklog`: Get worklog entries
- `jira_get_agile_boards`: Get agile boards
- `jira_get_sprints_from_board`: Get sprints
- `jira_get_user_profile`: Get user information

#### Write Operations
- `jira_create_issue`: Create new issue
- `jira_update_issue`: Update existing issue
- `jira_delete_issue`: Delete issue
- `jira_transition_issue`: Change issue status
- `jira_add_comment`: Add comment to issue
- `jira_add_worklog`: Add worklog entry
- `jira_link_to_epic`: Link issue to epic
- `jira_create_issue_link`: Create issue links

### Tool Function Signature Pattern

All Jira tools follow this pattern:

```python
@jira_mcp.tool(tags={"jira", "write"})
@check_write_access
async def create_issue(
    ctx: Context,  # FastMCP context (always first)
    project_key: Annotated[str, Field(description="...")],
    summary: Annotated[str, Field(description="...")],
    issue_type: Annotated[str, Field(description="...")],
    assignee: Annotated[str | None, Field(description="...", default=None)] = None,
    description: Annotated[str | None, Field(description="...", default=None)] = None,
    components: Annotated[str | None, Field(description="...", default=None)] = None,
    additional_fields: Annotated[dict[str, Any] | None, Field(description="...", default=None)] = None,
) -> str:
    """
    Create a new Jira issue.
    
    Returns:
        JSON string representing the created issue object.
    """
    jira = await get_jira_fetcher(ctx)  # Get client from context
    
    # Parse/validate inputs
    components_list = [c.strip() for c in components.split(",")] if components else None
    
    # Create issue using Jira client
    issue = jira.create_issue(
        project_key=project_key,
        summary=summary,
        issue_type=issue_type,
        description=description,
        assignee=assignee,
        components=components_list,
        **additional_fields or {},
    )
    
    # Return JSON response
    result = issue.to_simplified_dict()
    return json.dumps(
        {"message": "Issue created successfully", "issue": result},
        indent=2,
        ensure_ascii=False,
    )
```

### Response Format

Tools return JSON strings with standardized structure:

**Success Response:**
```json
{
  "message": "Issue created successfully",
  "issue": {
    "key": "PROJ-123",
    "summary": "Issue title",
    "status": "To Do",
    "url": "https://..."
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message",
  "issue_key": "PROJ-123"
}
```

---

## Integration Strategy

### How BugBridge Will Integrate

Since BugBridge already has access to MCP tools through the Cursor IDE, we have two options:

#### Option 1: Direct MCP Tool Calls (Recommended)
- Use existing MCP client infrastructure
- Call tools directly: `mcp_mcp-atlassian_jira_create_issue(...)`
- No need to create separate MCP client wrapper
- Simpler implementation

#### Option 2: MCP Client Wrapper
- Create wrapper in `bugbridge/integrations/mcp_jira.py`
- Abstract MCP protocol details
- Provide Python-native interface
- More work but cleaner abstraction

**Recommendation**: Use Option 1 (direct tool calls) for now since:
- Tools are already available through Cursor MCP integration
- Less code to maintain
- Direct access to all MCP features
- Can add wrapper later if needed

### Tool Call Pattern

```python
# In BugBridge agent code
from mcp import ClientSession

# Tools are already available through MCP client
result = await session.call_tool(
    "mcp_mcp-atlassian_jira_create_issue",
    {
        "project_key": "PROJ",
        "summary": "Bug: App crashes on button click",
        "issue_type": "Bug",
        "description": "...",
        "additional_fields": {
            "priority": {"name": "High"},
            "labels": ["bug", "urgent"]
        }
    }
)

# Parse JSON response
issue_data = json.loads(result.content[0].text)
issue_key = issue_data["issue"]["key"]
```

---

## Key Components

### 1. JiraFetcher Client

The `JiraFetcher` class (`mcp-atlassian/src/mcp_atlassian/jira/__init__.py`) wraps Atlassian Python API:

```python
class JiraFetcher:
    def create_issue(self, project_key, summary, issue_type, ...):
        # Creates issue via Atlassian API
        pass
    
    def get_issue(self, issue_key):
        # Gets issue details
        pass
    
    def search(self, jql):
        # Searches issues
        pass
```

### 2. Dependency Injection

Dependencies are injected through the `Context` object:

```python
from mcp_atlassian.servers.dependencies import get_jira_fetcher

async def create_issue(ctx: Context, ...):
    jira = await get_jira_fetcher(ctx)  # Gets configured JiraFetcher
```

The `get_jira_fetcher` function:
- Reads configuration from environment variables
- Initializes JiraFetcher with appropriate auth
- Handles OAuth, API tokens, or PATs
- Returns configured client instance

### 3. Configuration

Jira configuration is read from environment variables:
- `JIRA_URL`: Jira instance URL
- `JIRA_USERNAME`: Username (Cloud)
- `JIRA_API_TOKEN`: API token (Cloud)
- `JIRA_PERSONAL_TOKEN`: Personal Access Token (Server/DC)
- `JIRA_PROJECTS_FILTER`: Comma-separated project keys to filter

### 4. Authentication Methods

The server supports multiple auth methods:

**Cloud:**
- API Token: `JIRA_USERNAME` + `JIRA_API_TOKEN`
- OAuth 2.0: Various OAuth env vars

**Server/Data Center:**
- Personal Access Token: `JIRA_PERSONAL_TOKEN`

### 5. Error Handling

Tools use decorators and try/except for error handling:

```python
@check_write_access  # Checks read-only mode
async def create_issue(...):
    try:
        # Operation
    except Exception as e:
        # Return error JSON
        return json.dumps({"success": False, "error": str(e)})
```

---

## Key Insights for BugBridge Integration

### 1. Tool Naming Convention

MCP tools from `mcp-atlassian` server are prefixed with `mcp_mcp-atlassian_` when accessed through MCP client:
- Tool name in server: `create_issue`
- Tool name in MCP client: `mcp_mcp-atlassian_jira_create_issue`

### 2. Parameter Mapping

When calling MCP tools, parameters map directly:
- Python kwargs → MCP tool parameters
- Use same field names as defined in tool signature

### 3. Response Parsing

Tools return JSON strings that need parsing:
```python
response = await mcp_client.call_tool("...", {...})
result = json.loads(response.content[0].text)
```

### 4. Additional Fields Pattern

For complex fields (priority, labels, custom fields), use `additional_fields`:

```python
{
    "project_key": "PROJ",
    "summary": "...",
    "issue_type": "Bug",
    "additional_fields": {
        "priority": {"name": "High"},
        "labels": ["bug", "urgent"],
        "customfield_10010": "value"
    }
}
```

### 5. Issue Type Mapping

- Bug reports → `"Bug"`
- Feature requests → `"Story"` or `"Task"`
- Other requests → `"Task"`

---

## Integration Points for BugBridge

### Required Tools for BugBridge

1. **Create Issue** (`jira_create_issue`)
   - Primary tool for Jira Creation Agent
   - Maps analysis results to Jira ticket

2. **Get Issue** (`jira_get_issue`)
   - For Monitoring Agent
   - Check ticket status

3. **Update Issue** (`jira_update_issue`)
   - For updating ticket details
   - Status updates, adding information

4. **Search Issues** (`jira_search`)
   - For finding related issues
   - Monitoring multiple tickets

5. **Add Comment** (`jira_add_comment`)
   - For adding updates to tickets
   - Linking back to feedback

### Priority Mapping

Map `PriorityScoreResult.recommended_jira_priority` to Jira priority:
- `"Critical"` → `{"name": "Critical"}`
- `"High"` → `{"name": "High"}`
- `"Medium"` → `{"name": "Medium"}`
- `"Low"` → `{"name": "Low"}`

### Label Generation

Generate labels from analysis:
- Bug severity: `"bug-critical"`, `"bug-high"`, etc.
- Sentiment: `"negative-sentiment"`, `"urgent"`
- Source: `"canny-feedback"`, `"automated"`
- Custom tags from feedback post

---

## Next Steps

Based on this study, the integration approach should:

1. **Direct MCP Tool Usage**: Use tools directly through MCP client (already available)
2. **Wrapper Functions**: Create helper functions in `bugbridge/integrations/mcp_jira.py` that:
   - Wrap MCP tool calls
   - Handle JSON parsing
   - Provide Python-native interfaces
   - Map BugBridge models to MCP tool parameters

3. **LangChain Tools**: Create LangChain tools in `bugbridge/tools/jira_tools.py` that:
   - Wrap the helper functions
   - Provide structured inputs/outputs
   - Enable agents to use Jira operations

4. **Agent Implementation**: Implement Jira Creation Agent that:
   - Gathers analysis results
   - Formats Jira ticket data
   - Calls MCP tools through LangChain tools
   - Handles responses and updates state

---

## References

- MCP Protocol Specification: https://spec.modelcontextprotocol.io/
- FastMCP Documentation: https://github.com/jlowin/fastmcp
- mcp-atlassian Source: `/mcp-atlassian/` directory
- Available Tools: See `mcp-atlassian/src/mcp_atlassian/servers/jira.py`

