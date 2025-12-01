"""
Unit tests for Jira LangChain tools.

Tests the LangChain tools for MCP Jira operations including create, get, update,
search, add comment, and transition operations.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bugbridge.integrations.mcp_jira import (
    MCPJiraClient,
    MCPJiraError,
    MCPJiraNotFoundError,
)
from bugbridge.models.jira import JiraTicket, JiraTicketCreate
from bugbridge.tools.jira_tools import (
    create_add_comment_tool,
    create_create_issue_tool,
    create_get_issue_tool,
    create_search_issues_tool,
    create_transition_issue_tool,
    create_update_issue_tool,
    get_jira_tools,
)


def sample_jira_ticket(issue_key: str = "PROJ-123") -> JiraTicket:
    """Create a sample JiraTicket for testing."""
    return JiraTicket(
        id="10001",
        key=issue_key,
        project_key="PROJ",
        issue_type="Bug",
        priority="High",
        status="To Do",
        summary="Test Issue",
        description="Test description",
        labels=["bug", "urgent"],
        assignee="test@example.com",
        reporter="reporter@example.com",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        url=f"https://jira.example.com/browse/{issue_key}",
    )


@pytest.fixture
def mock_jira_client():
    """Create a mock MCPJiraClient."""
    client = MagicMock(spec=MCPJiraClient)
    client.connection = MagicMock()
    client.connection.__aenter__ = AsyncMock(return_value=None)
    client.connection.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.mark.asyncio
async def test_create_create_issue_tool(mock_jira_client):
    """create_create_issue_tool should create a tool that creates Jira issues."""
    mock_jira_client.create_issue = AsyncMock(return_value=sample_jira_ticket("PROJ-123"))

    tool = create_create_issue_tool(mock_jira_client)

    assert tool.name == "create_jira_issue"
    assert "Create a new Jira issue" in tool.description

    # Test tool invocation
    result = await tool.ainvoke(
        {
            "project_key": "PROJ",
            "summary": "Test Issue",
            "description": "Test description",
            "issue_type": "Bug",
            "priority": "High",
        }
    )

    assert isinstance(result, dict)
    assert result["key"] == "PROJ-123"
    mock_jira_client.create_issue.assert_called_once()


@pytest.mark.asyncio
async def test_create_issue_tool_with_all_fields(mock_jira_client):
    """create_create_issue_tool should handle all optional fields."""
    mock_jira_client.create_issue = AsyncMock(return_value=sample_jira_ticket("PROJ-123"))

    tool = create_create_issue_tool(mock_jira_client)

    result = await tool.ainvoke(
        {
            "project_key": "PROJ",
            "summary": "Test Issue",
            "description": "Test description",
            "issue_type": "Bug",
            "priority": "High",
            "labels": ["bug", "urgent"],
            "assignee": "test@example.com",
            "sentiment_score": 0.25,
            "priority_score": 75,
            "canny_post_url": "https://canny.io/post/123",
        }
    )

    assert result["key"] == "PROJ-123"
    call_args = mock_jira_client.create_issue.call_args[0][0]
    assert isinstance(call_args, JiraTicketCreate)
    assert call_args.project_key == "PROJ"
    assert call_args.summary == "Test Issue"
    assert call_args.labels == ["bug", "urgent"]
    assert call_args.assignee == "test@example.com"


@pytest.mark.asyncio
async def test_create_issue_tool_error_handling(mock_jira_client):
    """create_create_issue_tool should handle errors gracefully."""
    mock_jira_client.create_issue = AsyncMock(side_effect=MCPJiraError("Failed to create issue", tool_name="create_issue"))

    tool = create_create_issue_tool(mock_jira_client)

    result = await tool.ainvoke(
        {
            "project_key": "PROJ",
            "summary": "Test Issue",
            "description": "Test description",
            "issue_type": "Bug",
            "priority": "High",
        }
    )

    assert "error" in result
    assert "Failed to create issue" in result["error"]


@pytest.mark.asyncio
async def test_create_get_issue_tool(mock_jira_client):
    """create_get_issue_tool should create a tool that retrieves Jira issues."""
    mock_jira_client.get_issue = AsyncMock(return_value=sample_jira_ticket("PROJ-123"))

    tool = create_get_issue_tool(mock_jira_client)

    assert tool.name == "get_jira_issue"
    assert "Retrieve detailed information" in tool.description

    result = await tool.ainvoke({"issue_key": "PROJ-123"})

    assert isinstance(result, dict)
    assert result["key"] == "PROJ-123"
    mock_jira_client.get_issue.assert_called_once_with("PROJ-123", fields=None)


@pytest.mark.asyncio
async def test_get_issue_tool_with_fields(mock_jira_client):
    """create_get_issue_tool should support optional fields parameter."""
    mock_jira_client.get_issue = AsyncMock(return_value=sample_jira_ticket("PROJ-123"))

    tool = create_get_issue_tool(mock_jira_client)

    result = await tool.ainvoke({"issue_key": "PROJ-123", "fields": "summary,status,assignee"})

    mock_jira_client.get_issue.assert_called_once_with("PROJ-123", fields="summary,status,assignee")


@pytest.mark.asyncio
async def test_get_issue_tool_not_found(mock_jira_client):
    """create_get_issue_tool should handle not found errors."""
    mock_jira_client.get_issue = AsyncMock(side_effect=MCPJiraNotFoundError("Issue not found", tool_name="get_issue"))

    tool = create_get_issue_tool(mock_jira_client)

    result = await tool.ainvoke({"issue_key": "PROJ-999"})

    assert "error" in result
    assert "Issue not found" in result["error"]


@pytest.mark.asyncio
async def test_create_update_issue_tool(mock_jira_client):
    """create_update_issue_tool should create a tool that updates Jira issues."""
    updated_ticket = sample_jira_ticket("PROJ-123")
    updated_ticket.summary = "Updated Summary"
    mock_jira_client.update_issue = AsyncMock(return_value=updated_ticket)

    tool = create_update_issue_tool(mock_jira_client)

    assert tool.name == "update_jira_issue"
    assert "Update a Jira issue" in tool.description

    result = await tool.ainvoke({"issue_key": "PROJ-123", "fields": {"summary": "Updated Summary"}})

    assert isinstance(result, dict)
    assert result["summary"] == "Updated Summary"
    mock_jira_client.update_issue.assert_called_once_with(
        issue_key="PROJ-123",
        fields={"summary": "Updated Summary"},
        additional_fields=None,
    )


@pytest.mark.asyncio
async def test_update_issue_tool_with_additional_fields(mock_jira_client):
    """create_update_issue_tool should support additional_fields parameter."""
    updated_ticket = sample_jira_ticket("PROJ-123")
    mock_jira_client.update_issue = AsyncMock(return_value=updated_ticket)

    tool = create_update_issue_tool(mock_jira_client)

    result = await tool.ainvoke(
        {
            "issue_key": "PROJ-123",
            "fields": {"summary": "Updated"},
            "additional_fields": {"priority": {"name": "Critical"}},
        }
    )

    mock_jira_client.update_issue.assert_called_once_with(
        issue_key="PROJ-123",
        fields={"summary": "Updated"},
        additional_fields={"priority": {"name": "Critical"}},
    )


@pytest.mark.asyncio
async def test_create_search_issues_tool(mock_jira_client):
    """create_search_issues_tool should create a tool that searches Jira issues."""
    tickets = [sample_jira_ticket("PROJ-123"), sample_jira_ticket("PROJ-124")]
    mock_jira_client.search_issues = AsyncMock(return_value=tickets)

    tool = create_search_issues_tool(mock_jira_client)

    assert tool.name == "search_jira_issues"
    assert "Search for Jira issues using JQL" in tool.description

    result = await tool.ainvoke({"jql": "project = PROJ AND status = Open", "limit": 50})

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["key"] == "PROJ-123"
    assert result[1]["key"] == "PROJ-124"
    mock_jira_client.search_issues.assert_called_once_with(jql="project = PROJ AND status = Open", limit=50, fields=None)


@pytest.mark.asyncio
async def test_search_issues_tool_with_fields(mock_jira_client):
    """create_search_issues_tool should support optional fields parameter."""
    tickets = [sample_jira_ticket("PROJ-123")]
    mock_jira_client.search_issues = AsyncMock(return_value=tickets)

    tool = create_search_issues_tool(mock_jira_client)

    result = await tool.ainvoke(
        {"jql": "project = PROJ", "limit": 50, "fields": "summary,status,assignee"}
    )

    mock_jira_client.search_issues.assert_called_once_with(
        jql="project = PROJ", limit=50, fields="summary,status,assignee"
    )


@pytest.mark.asyncio
async def test_search_issues_tool_empty_results(mock_jira_client):
    """create_search_issues_tool should handle empty search results."""
    mock_jira_client.search_issues = AsyncMock(return_value=[])

    tool = create_search_issues_tool(mock_jira_client)

    result = await tool.ainvoke({"jql": "project = PROJ AND status = Closed", "limit": 50})

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_create_add_comment_tool(mock_jira_client):
    """create_add_comment_tool should create a tool that adds comments to Jira issues."""
    mock_jira_client.add_comment = AsyncMock(return_value={"id": "10001", "body": "Test comment"})

    tool = create_add_comment_tool(mock_jira_client)

    assert tool.name == "add_jira_comment"
    assert "Add a comment to a Jira issue" in tool.description

    result = await tool.ainvoke({"issue_key": "PROJ-123", "comment": "Test comment"})

    assert isinstance(result, dict)
    assert result["id"] == "10001"
    mock_jira_client.add_comment.assert_called_once_with(issue_key="PROJ-123", comment="Test comment")


@pytest.mark.asyncio
async def test_create_transition_issue_tool(mock_jira_client):
    """create_transition_issue_tool should create a tool that transitions Jira issues."""
    transitioned_ticket = sample_jira_ticket("PROJ-123")
    transitioned_ticket.status = "In Progress"
    mock_jira_client.transition_issue = AsyncMock(return_value=transitioned_ticket)

    tool = create_transition_issue_tool(mock_jira_client)

    assert tool.name == "transition_jira_issue"
    assert "Transition a Jira issue to a new status" in tool.description

    result = await tool.ainvoke(
        {
            "issue_key": "PROJ-123",
            "transition_id": "21",
            "comment": "Starting work",
            "fields": {"assignee": "dev@example.com"},
        }
    )

    assert isinstance(result, dict)
    assert result["status"] == "In Progress"
    mock_jira_client.transition_issue.assert_called_once_with(
        issue_key="PROJ-123",
        transition_id="21",
        comment="Starting work",
        fields={"assignee": "dev@example.com"},
    )


@pytest.mark.asyncio
async def test_transition_issue_tool_without_optional_fields(mock_jira_client):
    """create_transition_issue_tool should work without optional fields."""
    transitioned_ticket = sample_jira_ticket("PROJ-123")
    mock_jira_client.transition_issue = AsyncMock(return_value=transitioned_ticket)

    tool = create_transition_issue_tool(mock_jira_client)

    result = await tool.ainvoke({"issue_key": "PROJ-123", "transition_id": "21"})

    mock_jira_client.transition_issue.assert_called_once_with(
        issue_key="PROJ-123",
        transition_id="21",
        comment=None,
        fields=None,
    )


@pytest.mark.asyncio
async def test_get_jira_tools(mock_jira_client):
    """get_jira_tools should return all Jira tools."""
    tools = get_jira_tools(mock_jira_client)

    assert len(tools) == 6
    tool_names = {tool.name for tool in tools}
    expected_names = {
        "create_jira_issue",
        "get_jira_issue",
        "update_jira_issue",
        "search_jira_issues",
        "add_jira_comment",
        "transition_jira_issue",
    }
    assert tool_names == expected_names


@pytest.mark.asyncio
async def test_tool_input_schemas():
    """Tool input schemas should validate correctly."""
    from bugbridge.tools.jira_tools import (
        AddCommentInput,
        CreateIssueInput,
        GetIssueInput,
        SearchIssuesInput,
        TransitionIssueInput,
        UpdateIssueInput,
    )

    # CreateIssueInput
    create_input = CreateIssueInput(
        project_key="PROJ",
        summary="Test",
        description="Test description",
        issue_type="Bug",
        priority="High",
    )
    assert create_input.project_key == "PROJ"
    assert create_input.issue_type == "Bug"

    # GetIssueInput
    get_input = GetIssueInput(issue_key="PROJ-123")
    assert get_input.issue_key == "PROJ-123"

    # UpdateIssueInput
    update_input = UpdateIssueInput(issue_key="PROJ-123", fields={"summary": "Updated"})
    assert update_input.issue_key == "PROJ-123"
    assert update_input.fields == {"summary": "Updated"}

    # SearchIssuesInput
    search_input = SearchIssuesInput(jql="project = PROJ", limit=50)
    assert search_input.jql == "project = PROJ"
    assert search_input.limit == 50

    # AddCommentInput
    comment_input = AddCommentInput(issue_key="PROJ-123", comment="Test comment")
    assert comment_input.issue_key == "PROJ-123"
    assert comment_input.comment == "Test comment"

    # TransitionIssueInput
    transition_input = TransitionIssueInput(issue_key="PROJ-123", transition_id="21")
    assert transition_input.issue_key == "PROJ-123"
    assert transition_input.transition_id == "21"


@pytest.mark.asyncio
async def test_tool_error_handling_unexpected_error(mock_jira_client):
    """Tools should handle unexpected errors gracefully."""
    mock_jira_client.create_issue = AsyncMock(side_effect=ValueError("Unexpected error"))

    tool = create_create_issue_tool(mock_jira_client)

    result = await tool.ainvoke(
        {
            "project_key": "PROJ",
            "summary": "Test Issue",
            "description": "Test description",
            "issue_type": "Bug",
            "priority": "High",
        }
    )

    assert "error" in result
    assert "Unexpected error" in result["error"]

