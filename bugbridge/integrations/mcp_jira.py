"""
MCP Jira Client Wrapper

This module provides a Python-native wrapper around MCP (Model Context Protocol) Jira tools.
It abstracts away MCP protocol details and provides clean interfaces for Jira operations.

The wrapper can work in two modes:
1. With a provided MCP client session (when running in an environment with MCP support)
2. With direct MCP server connection via HTTP/Streamable transport (task 7.3)
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from bugbridge.config import get_settings
from bugbridge.models.jira import JiraTicket, JiraTicketCreate
from bugbridge.utils.logging import get_logger
from bugbridge.utils.retry import async_retry_with_backoff

logger = get_logger(__name__)

# MCP tool name prefix - tools from mcp-atlassian server use this prefix
# Note: When connecting directly, tool names don't include the prefix
MCP_TOOL_PREFIX = "mcp_mcp-atlassian_jira_"
MCP_TOOL_PREFIX_DIRECT = "jira_"  # Direct connection uses unprefixed names


class MCPJiraError(Exception):
    """Base exception for MCP Jira operations."""

    def __init__(self, message: str, tool_name: Optional[str] = None, response: Optional[Dict[str, Any]] = None):
        """Initialize MCP Jira error with message, tool name, and response."""
        super().__init__(message)
        self.tool_name = tool_name
        self.response = response
        self.is_retryable = True  # Default to retryable unless explicitly set


class MCPJiraConnectionError(MCPJiraError):
    """Raised when MCP connection fails (retryable)."""

    def __init__(self, message: str, tool_name: Optional[str] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message, tool_name, response)
        self.is_retryable = True


class MCPJiraAuthenticationError(MCPJiraError):
    """Raised when authentication fails (non-retryable)."""

    def __init__(self, message: str, tool_name: Optional[str] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message, tool_name, response)
        self.is_retryable = False


class MCPJiraRateLimitError(MCPJiraError):
    """Raised when rate limit is exceeded (retryable with backoff)."""

    def __init__(self, message: str, retry_after: Optional[int] = None, tool_name: Optional[str] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message, tool_name, response)
        self.is_retryable = True
        self.retry_after = retry_after


class MCPJiraValidationError(MCPJiraError):
    """Raised when request validation fails (non-retryable)."""

    def __init__(self, message: str, tool_name: Optional[str] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message, tool_name, response)
        self.is_retryable = False


class MCPJiraNotFoundError(MCPJiraError):
    """Raised when resource is not found (non-retryable)."""

    def __init__(self, message: str, tool_name: Optional[str] = None, response: Optional[Dict[str, Any]] = None):
        super().__init__(message, tool_name, response)
        self.is_retryable = False


class MCPJiraClient:
    """
    Client wrapper for MCP Jira operations.

    This wrapper provides a Python-native interface to Jira operations through
    the MCP (Model Context Protocol) server. It handles tool invocation,
    response parsing, and error handling.

    The client can work with:
    - An MCP client session (provided via set_session method)
    - Direct MCP server connection via HTTP/Streamable transport
    """

    def __init__(
        self,
        mcp_session: Optional[Any] = None,
        server_url: Optional[str] = None,
        project_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None,
        auto_connect: bool = True,
    ):
        """
        Initialize the MCP Jira client.

        Args:
            mcp_session: Optional MCP client session. If provided, will be used
                for all tool calls. Takes precedence over server_url.
            server_url: Optional MCP server URL for direct connection.
                If not provided, will be loaded from settings.
                Format: "http://localhost:9000/mcp" or "http://localhost:9000/sse"
            project_key: Default Jira project key to use for operations.
                If not provided, will be loaded from settings.
            timeout: Request timeout in seconds.
            max_retries: Maximum number of retry attempts for failed requests.
            headers: Optional HTTP headers for authentication (e.g., Authorization).
            auto_connect: If True and server_url is provided, will attempt to connect
                automatically on first use. If False, must call connect() manually.
        """
        self._mcp_session = mcp_session
        self._timeout = timeout
        self._max_retries = max_retries
        self._headers = headers or {}
        self._auto_connect = auto_connect
        self._connection_context = None  # For managing connection lifecycle
        self._is_connected = False

        # Determine server URL
        if server_url:
            self._server_url = str(server_url)
        else:
            try:
                settings = get_settings()
                self._server_url = str(settings.jira.server_url)
            except Exception as e:
                logger.warning(f"Could not load server URL from settings: {e}")
                self._server_url = None

        # Determine if we're using direct connection (via server_url) or provided session
        self._use_direct_connection = self._server_url is not None and self._mcp_session is None

        # Load default project key from settings if not provided
        if project_key:
            self._default_project_key = project_key
        else:
            try:
                settings = get_settings()
                self._default_project_key = settings.jira.project_key
            except Exception as e:
                logger.warning(f"Could not load default project key from settings: {e}")
                self._default_project_key = None

    def set_session(self, mcp_session: Any) -> None:
        """
        Set the MCP client session to use for tool calls.

        Args:
            mcp_session: MCP client session instance.
        """
        self._mcp_session = mcp_session
        self._use_direct_connection = False  # Using provided session instead
        logger.debug("MCP client session set for Jira operations")

    @async_retry_with_backoff(
        max_retries=3,
        base_delay=1.0,
        exceptions=(MCPJiraConnectionError, ConnectionError, TimeoutError),
    )
    async def connect(self) -> None:
        """
        Establish connection to MCP server if using direct connection mode.

        This method should be called before using the client if auto_connect is False
        and server_url is configured. It can also be called to reconnect after
        a connection loss.

        Raises:
            MCPJiraError: If connection fails or server_url is not configured.
        """
        if not self._use_direct_connection:
            logger.debug("Not using direct connection, skipping connect()")
            return

        if not self._server_url:
            raise MCPJiraError("Cannot connect: server_url not configured")

        if self._is_connected:
            logger.debug("Already connected to MCP server")
            return

        try:
            # Try to import MCP client libraries
            try:
                from mcp.client.streamable_http import streamablehttp_client
                from mcp import ClientSession
            except ImportError as e:
                raise MCPJiraError(
                    "MCP client libraries not available. Install with: pip install mcp",
                    response={"import_error": str(e)},
                ) from e

            logger.info(f"Connecting to MCP server at {self._server_url}")

            # Determine transport type from URL
            # Default to streamable-http, use SSE if URL contains /sse
            if "/sse" in self._server_url.lower():
                try:
                    from mcp.client.sse import sse_client
                    client_factory = sse_client
                except ImportError:
                    # Fallback to streamable-http if SSE not available
                    logger.warning("SSE client not available, falling back to streamable-http")
                    client_factory = streamablehttp_client
            else:
                client_factory = streamablehttp_client

            # Create connection context
            connection_ctx = client_factory(self._server_url, headers=self._headers or {})
            read_stream, write_stream, _ = await connection_ctx.__aenter__()

            # Create session
            session = ClientSession(read_stream, write_stream)
            await session.__aenter__()
            await session.initialize()

            # Store connection context for cleanup
            self._mcp_session = session
            self._connection_context = connection_ctx
            self._is_connected = True

            logger.info("Successfully connected to MCP server")

        except ConnectionError as e:
            logger.error(f"Connection error connecting to MCP server: {str(e)}", exc_info=True)
            raise MCPJiraConnectionError(f"Failed to connect to MCP server: {str(e)}") from e
        except TimeoutError as e:
            logger.error(f"Timeout connecting to MCP server: {str(e)}", exc_info=True)
            raise MCPJiraConnectionError(f"Connection timeout to MCP server: {str(e)}") from e
        except Exception as e:
            error_msg = str(e)
            # Check for authentication-related errors
            if "authentication" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                raise MCPJiraAuthenticationError(f"Authentication failed connecting to MCP server: {error_msg}") from e
            logger.error(f"Failed to connect to MCP server: {error_msg}", exc_info=True)
            raise MCPJiraConnectionError(f"Failed to connect to MCP server: {error_msg}") from e

    async def disconnect(self) -> None:
        """
        Disconnect from MCP server and clean up resources.

        This method should be called when done with the client to properly
        close connections and free resources.
        """
        if not self._is_connected:
            return

        try:
            # Close session if it exists
            if self._mcp_session and hasattr(self._mcp_session, "__aexit__"):
                await self._mcp_session.__aexit__(None, None, None)

            # Close connection context if it exists
            if self._connection_context and hasattr(self._connection_context, "__aexit__"):
                await self._connection_context.__aexit__(None, None, None)

            self._mcp_session = None
            self._connection_context = None
            self._is_connected = False

            logger.debug("Disconnected from MCP server")

        except Exception as e:
            logger.warning(f"Error during disconnect: {str(e)}", exc_info=True)

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[None, None]:
        """
        Context manager for managing MCP server connection lifecycle.

        Usage:
            async with client.connection():
                issue = await client.get_issue("PROJ-123")
        """
        try:
            if not self._is_connected:
                await self.connect()
            yield
        finally:
            await self.disconnect()

    async def __aenter__(self) -> MCPJiraClient:
        """Async context manager entry - auto-connects if enabled."""
        if self._auto_connect and self._use_direct_connection:
            await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit - disconnects."""
        await self.disconnect()

    async def _call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal method to call an MCP tool and parse the response.

        Args:
            tool_name: Name of the MCP tool (without prefix).
            arguments: Arguments to pass to the tool.

        Returns:
            Parsed JSON response as a dictionary.

        Raises:
            MCPJiraError: If the tool call fails or session is not available.
        """
        # Auto-connect if needed
        if self._use_direct_connection and not self._is_connected and self._auto_connect:
            await self.connect()

        if not self._mcp_session:
            raise MCPJiraError(
                "MCP client session not available. Set session using set_session(), call connect(), "
                "or configure server_url and enable auto_connect.",
                tool_name=tool_name,
            )

        # Construct full tool name with appropriate prefix
        # Direct connections use unprefixed names, provided sessions use prefixed
        if self._use_direct_connection:
            full_tool_name = f"{MCP_TOOL_PREFIX_DIRECT}{tool_name}"
        else:
            full_tool_name = f"{MCP_TOOL_PREFIX}{tool_name}"

        logger.info(f"Calling MCP tool: {full_tool_name} with arguments: {json.dumps(arguments, default=str)[:500]}")

        try:
            # Call the MCP tool through the session
            # Note: This assumes the MCP session has a call_tool method
            # The exact interface may vary depending on the MCP client implementation
            if hasattr(self._mcp_session, "call_tool"):
                result = await self._mcp_session.call_tool(full_tool_name, arguments)
            elif hasattr(self._mcp_session, "callTool"):
                result = await self._mcp_session.callTool(full_tool_name, arguments)
            else:
                # Try to access via list_mcp_resources or fetch_mcp_resource if available
                # This is a fallback for when MCP tools are available via global functions
                raise MCPJiraError(
                    f"MCP session does not have a recognized call_tool method. Available methods: {dir(self._mcp_session)}",
                    tool_name=tool_name,
                )

            # Parse the response
            # MCP tools typically return TextContent objects with JSON strings
            if hasattr(result, "content") and result.content:
                # Extract text from content
                if isinstance(result.content, list) and len(result.content) > 0:
                    text_content = result.content[0]
                    if hasattr(text_content, "text"):
                        response_text = text_content.text
                    elif isinstance(text_content, str):
                        response_text = text_content
                    else:
                        response_text = str(text_content)
                else:
                    response_text = str(result.content)
            elif isinstance(result, str):
                response_text = result
            else:
                response_text = json.dumps(result) if result else "{}"

            # Parse JSON response
            try:
                parsed_response = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP tool response as JSON: {response_text[:200]}")
                raise MCPJiraError(
                    f"Invalid JSON response from MCP tool: {str(e)}",
                    tool_name=tool_name,
                    response={"raw": response_text},
                )

            # Check for error in response
            if isinstance(parsed_response, dict) and parsed_response.get("success") is False:
                error_msg = parsed_response.get("error", "Unknown error from MCP tool")
                error_type = parsed_response.get("error_type", "").lower()
                status_code = parsed_response.get("status_code")

                # Classify errors based on error type or status code
                if status_code == 401 or "authentication" in error_type or "unauthorized" in error_msg.lower():
                    raise MCPJiraAuthenticationError(
                        f"Authentication failed: {error_msg}",
                        tool_name=tool_name,
                        response=parsed_response,
                    )
                elif status_code == 404 or "not found" in error_msg.lower():
                    raise MCPJiraNotFoundError(
                        f"Resource not found: {error_msg}",
                        tool_name=tool_name,
                        response=parsed_response,
                    )
                elif status_code == 429 or "rate limit" in error_msg.lower():
                    retry_after = parsed_response.get("retry_after")
                    raise MCPJiraRateLimitError(
                        f"Rate limit exceeded: {error_msg}",
                        retry_after=retry_after,
                        tool_name=tool_name,
                        response=parsed_response,
                    )
                elif status_code in (400, 422) or "validation" in error_type or "invalid" in error_msg.lower():
                    raise MCPJiraValidationError(
                        f"Validation error: {error_msg}",
                        tool_name=tool_name,
                        response=parsed_response,
                    )
                else:
                    # Generic error, may be retryable depending on status code
                    error = MCPJiraError(
                        f"MCP tool returned error: {error_msg}",
                        tool_name=tool_name,
                        response=parsed_response,
                    )
                    # Non-4xx/5xx errors are retryable
                    error.is_retryable = status_code is None or status_code >= 500
                    raise error

            return parsed_response

        except (
            MCPJiraError,
            MCPJiraAuthenticationError,
            MCPJiraRateLimitError,
            MCPJiraValidationError,
            MCPJiraNotFoundError,
            MCPJiraConnectionError,
        ):
            # Re-raise our custom errors as-is
            raise
        except ConnectionError as e:
            logger.error(f"Connection error calling MCP tool {tool_name}: {str(e)}", exc_info=True)
            raise MCPJiraConnectionError(
                f"Connection failed to MCP tool {tool_name}: {str(e)}",
                tool_name=tool_name,
            ) from e
        except TimeoutError as e:
            logger.error(f"Timeout calling MCP tool {tool_name}: {str(e)}", exc_info=True)
            raise MCPJiraConnectionError(
                f"Timeout calling MCP tool {tool_name}: {str(e)}",
                tool_name=tool_name,
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error calling MCP tool {tool_name}: {str(e)}", exc_info=True)
            # For unexpected errors, assume retryable unless we can determine otherwise
            error = MCPJiraError(
                f"Failed to call MCP tool {tool_name}: {str(e)}",
                tool_name=tool_name,
            )
            error.is_retryable = True
            raise error

    @async_retry_with_backoff(
        max_retries=3,
        exceptions=(
            MCPJiraError,
            MCPJiraConnectionError,
            MCPJiraRateLimitError,
            ConnectionError,
            TimeoutError,
        ),
    )
    async def create_issue(self, ticket_data: JiraTicketCreate) -> JiraTicket:
        """
        Create a new Jira issue from ticket data.

        Args:
            ticket_data: JiraTicketCreate object with issue details.

        Returns:
            JiraTicket object representing the created issue.

        Raises:
            MCPJiraError: If issue creation fails.
        """
        logger.info(f"Creating Jira issue in project {ticket_data.project_key}: {ticket_data.summary}")

        # Prepare additional_fields with priority, labels, and custom metadata
        additional_fields: Dict[str, Any] = {}
        
        # Note: Next-gen Jira projects may not support priority field via API
        # Skip priority field to avoid errors with next-gen projects
        # if ticket_data.priority:
        #     additional_fields["priority"] = {"name": ticket_data.priority}

        if ticket_data.labels:
            additional_fields["labels"] = ticket_data.labels

        # Add custom fields if provided in metadata
        if ticket_data.metadata:
            for key, value in ticket_data.metadata.items():
                if key.startswith("customfield_"):
                    additional_fields[key] = value

        # Prepare MCP tool arguments
        tool_args: Dict[str, Any] = {
            "project_key": ticket_data.project_key,
            "summary": ticket_data.summary,
            "issue_type": ticket_data.issue_type,
            "description": ticket_data.description,
            "additional_fields": additional_fields,
        }

        if ticket_data.assignee:
            tool_args["assignee"] = ticket_data.assignee

        if ticket_data.reporter:
            tool_args["reporter"] = ticket_data.reporter

        # Call MCP tool
        response = await self._call_mcp_tool("create_issue", tool_args)

        # Parse response and create JiraTicket object
        issue_data = response.get("issue", {})
        if not issue_data:
            raise MCPJiraError("Response missing 'issue' field", tool_name="create_issue", response=response)

        return self._parse_issue_response(issue_data, ticket_data)

    @async_retry_with_backoff(
        max_retries=3,
        exceptions=(
            MCPJiraError,
            MCPJiraConnectionError,
            MCPJiraRateLimitError,
            ConnectionError,
            TimeoutError,
        ),
    )
    async def get_issue(self, issue_key: str, fields: Optional[str] = None) -> JiraTicket:
        """
        Get details of a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123").
            fields: Optional comma-separated list of fields to return.
                Defaults to essential fields.

        Returns:
            JiraTicket object with issue details.

        Raises:
            MCPJiraError: If issue retrieval fails.
        """
        logger.debug(f"Fetching Jira issue: {issue_key}")

        tool_args: Dict[str, Any] = {"issue_key": issue_key}
        if fields:
            tool_args["fields"] = fields

        response = await self._call_mcp_tool("get_issue", tool_args)

        # Parse response - MCP get_issue returns issue data directly or in 'issue' field
        issue_data = response.get("issue") if isinstance(response, dict) and "issue" in response else response

        if not issue_data:
            raise MCPJiraError("Response missing issue data", tool_name="get_issue", response=response)

        return self._parse_issue_response(issue_data)

    @async_retry_with_backoff(
        max_retries=3,
        exceptions=(
            MCPJiraError,
            MCPJiraConnectionError,
            MCPJiraRateLimitError,
            ConnectionError,
            TimeoutError,
        ),
    )
    async def update_issue(
        self,
        issue_key: str,
        fields: Optional[Dict[str, Any]] = None,
        additional_fields: Optional[Dict[str, Any]] = None,
    ) -> JiraTicket:
        """
        Update a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123").
            fields: Dictionary of fields to update (e.g., {"summary": "New title"}).
            additional_fields: Additional fields dictionary for complex updates.

        Returns:
            Updated JiraTicket object.

        Raises:
            MCPJiraError: If issue update fails.
        """
        logger.info(f"Updating Jira issue: {issue_key}")

        tool_args: Dict[str, Any] = {"issue_key": issue_key}

        if fields:
            tool_args["fields"] = fields

        if additional_fields:
            tool_args["additional_fields"] = additional_fields

        response = await self._call_mcp_tool("update_issue", tool_args)

        # Parse response
        issue_data = response.get("issue") if isinstance(response, dict) and "issue" in response else response

        if not issue_data:
            raise MCPJiraError("Response missing issue data", tool_name="update_issue", response=response)

        return self._parse_issue_response(issue_data)

    @async_retry_with_backoff(
        max_retries=3,
        exceptions=(
            MCPJiraError,
            MCPJiraConnectionError,
            MCPJiraRateLimitError,
            ConnectionError,
            TimeoutError,
        ),
    )
    async def search_issues(self, jql: str, limit: int = 50, fields: Optional[str] = None) -> List[JiraTicket]:
        """
        Search for Jira issues using JQL.

        Args:
            jql: JQL query string.
            limit: Maximum number of results (1-100, default 50).
            fields: Optional comma-separated list of fields to return.

        Returns:
            List of JiraTicket objects matching the query.

        Raises:
            MCPJiraError: If search fails.
        """
        logger.debug(f"Searching Jira issues with JQL: {jql}")

        tool_args: Dict[str, Any] = {
            "jql": jql,
            "limit": min(max(limit, 1), 100),  # Clamp between 1 and 100
        }

        if fields:
            tool_args["fields"] = fields

        response = await self._call_mcp_tool("search", tool_args)

        # Parse response - search returns issues in 'issues' array
        issues_data = response.get("issues", [])
        if not issues_data:
            return []

        return [self._parse_issue_response(issue_data) for issue_data in issues_data]

    @async_retry_with_backoff(
        max_retries=3,
        exceptions=(
            MCPJiraError,
            MCPJiraConnectionError,
            MCPJiraRateLimitError,
            ConnectionError,
            TimeoutError,
        ),
    )
    async def add_comment(self, issue_key: str, comment: str) -> Dict[str, Any]:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123").
            comment: Comment text (Markdown format supported).

        Returns:
            Dictionary with comment details.

        Raises:
            MCPJiraError: If adding comment fails.
        """
        logger.debug(f"Adding comment to Jira issue: {issue_key}")

        tool_args: Dict[str, Any] = {
            "issue_key": issue_key,
            "comment": comment,
        }

        response = await self._call_mcp_tool("add_comment", tool_args)
        return response

    @async_retry_with_backoff(
        max_retries=3,
        exceptions=(
            MCPJiraError,
            MCPJiraConnectionError,
            MCPJiraRateLimitError,
            ConnectionError,
            TimeoutError,
        ),
    )
    async def transition_issue(
        self, issue_key: str, transition_id: str, comment: Optional[str] = None, fields: Optional[Dict[str, Any]] = None
    ) -> JiraTicket:
        """
        Transition a Jira issue to a new status.

        Args:
            issue_key: Jira issue key (e.g., "PROJ-123").
            transition_id: ID of the transition to perform.
            comment: Optional comment for the transition.
            fields: Optional dictionary of fields to update during transition.

        Returns:
            Updated JiraTicket object.

        Raises:
            MCPJiraError: If transition fails.
        """
        logger.info(f"Transitioning Jira issue {issue_key} to transition {transition_id}")

        tool_args: Dict[str, Any] = {
            "issue_key": issue_key,
            "transition_id": transition_id,
        }

        if comment:
            tool_args["comment"] = comment

        if fields:
            tool_args["fields"] = fields

        response = await self._call_mcp_tool("transition_issue", tool_args)

        # Parse response
        issue_data = response.get("issue") if isinstance(response, dict) and "issue" in response else response

        if not issue_data:
            raise MCPJiraError("Response missing issue data", tool_name="transition_issue", response=response)

        return self._parse_issue_response(issue_data)

    def _parse_issue_response(self, issue_data: Dict[str, Any], ticket_create: Optional[JiraTicketCreate] = None) -> JiraTicket:
        """
        Parse raw issue data from MCP response into a JiraTicket object.

        Args:
            issue_data: Raw issue data dictionary from MCP response.
            ticket_create: Optional JiraTicketCreate object to merge metadata from.

        Returns:
            JiraTicket object.
        """
        # Extract common fields from issue data
        key = issue_data.get("key") or issue_data.get("id")
        if not key:
            raise MCPJiraError("Issue response missing key/id field", response=issue_data)

        # Parse timestamps
        created_str = issue_data.get("created") or issue_data.get("created_at")
        updated_str = issue_data.get("updated") or issue_data.get("updated_at")
        resolved_str = issue_data.get("resolved") or issue_data.get("resolved_at")

        created_at = self._parse_datetime(created_str) if created_str else datetime.now(UTC)
        updated_at = self._parse_datetime(updated_str) if updated_str else created_at
        resolved_at = self._parse_datetime(resolved_str) if resolved_str else None

        # Extract project key from issue key (e.g., "PROJ-123" -> "PROJ")
        project_key = key.split("-")[0] if "-" in key else (ticket_create.project_key if ticket_create else None)

        # Extract priority
        priority_str = "Medium"
        if isinstance(issue_data.get("priority"), dict):
            priority_str = issue_data["priority"].get("name", "Medium")
        elif isinstance(issue_data.get("priority"), str):
            priority_str = issue_data["priority"]

        # Map priority string to allowed Literal values
        priority_map = {"Critical": "Critical", "High": "High", "Medium": "Medium", "Low": "Low"}
        priority = priority_map.get(priority_str, "Medium")

        # Extract status
        status = "To Do"
        if isinstance(issue_data.get("status"), dict):
            status = issue_data["status"].get("name", "To Do")
        elif isinstance(issue_data.get("status"), str):
            status = issue_data["status"]

        # Extract assignee
        assignee = None
        if isinstance(issue_data.get("assignee"), dict):
            assignee = issue_data["assignee"].get("displayName") or issue_data["assignee"].get("emailAddress") or issue_data["assignee"].get("accountId")
        elif isinstance(issue_data.get("assignee"), str):
            assignee = issue_data["assignee"]

        # Extract reporter
        reporter = None
        if isinstance(issue_data.get("reporter"), dict):
            reporter = issue_data["reporter"].get("displayName") or issue_data["reporter"].get("emailAddress")
        elif isinstance(issue_data.get("reporter"), str):
            reporter = issue_data["reporter"]

        # Extract labels
        labels = issue_data.get("labels", [])
        if not isinstance(labels, list):
            labels = []

        # Extract URL
        url = issue_data.get("url") or issue_data.get("self")
        if url and isinstance(url, str):
            # Convert API self URL to browser URL if needed
            if "/rest/api/" in url:
                url = url.replace("/rest/api/3/issue/", "/browse/")

        # Extract issue_type (can be string or dict with "name")
        issue_type_data = issue_data.get("issue_type")
        if isinstance(issue_type_data, dict):
            issue_type = issue_type_data.get("name", "Task")
        elif isinstance(issue_type_data, str):
            issue_type = issue_type_data
        else:
            issue_type = "Task"  # Default fallback

        # Merge metadata from ticket_create if provided
        sentiment_score = ticket_create.sentiment_score if ticket_create else None
        priority_score = ticket_create.priority_score if ticket_create else None
        canny_post_url = ticket_create.canny_post_url if ticket_create else None

        return JiraTicket(
            id=str(issue_data.get("id", "")),
            key=key,
            project_key=project_key or self._default_project_key or "UNKNOWN",
            issue_type=issue_type,
            priority=priority,
            status=status,
            summary=issue_data.get("summary", ""),
            description=issue_data.get("description"),
            labels=labels,
            assignee=assignee,
            reporter=reporter,
            canny_post_url=canny_post_url,
            sentiment_score=sentiment_score,
            priority_score=priority_score,
            created_at=created_at,
            updated_at=updated_at,
            resolved_at=resolved_at,
            url=url,
        )

    @staticmethod
    def _parse_datetime(dt_str: str) -> Optional[datetime]:
        """
        Parse datetime string from various formats into datetime object.

        Args:
            dt_str: Datetime string in various formats.

        Returns:
            datetime object or None if parsing fails.
        """
        if not dt_str:
            return None

        # Try ISO format first
        try:
            # Handle ISO format with timezone
            if dt_str.endswith("Z"):
                dt_str = dt_str[:-1] + "+00:00"
            elif "+" not in dt_str and "-" in dt_str[-6:]:
                # Already has timezone
                pass

            # Try parsing with dateutil for flexibility
            from dateutil import parser

            return parser.parse(dt_str).replace(tzinfo=UTC)
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{dt_str}': {e}")
            return None

