"""
LangChain Tools for MCP Jira Integration

Tools that enable AI agents to interact with Jira through the MCP (Model Context Protocol) server
for creating tickets, retrieving issue details, updating issues, and searching.
"""

from __future__ import annotations

from typing import List, Literal, Optional

from langchain.tools import BaseTool, tool
from pydantic import BaseModel, Field

from bugbridge.integrations.mcp_jira import MCPJiraClient, MCPJiraError
from bugbridge.models.jira import JiraTicket, JiraTicketCreate
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


class CreateIssueInput(BaseModel):
    """Input schema for CreateIssueTool."""

    project_key: str = Field(..., description="Jira project key (e.g., 'PROJ')")
    summary: str = Field(..., min_length=1, max_length=255, description="Summary/title of the Jira issue")
    description: str = Field(..., description="Rich description including feedback context")
    issue_type: Literal["Bug", "Story", "Task", "Epic", "Incident", "Service Request"] = Field(
        "Bug", description="Jira issue type"
    )
    priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        "Medium", description="Priority level mapped from priority score"
    )
    labels: List[str] = Field(default_factory=list, description="Labels/tags to apply in Jira")
    assignee: Optional[str] = Field(
        None, description="User to assign the ticket to (account ID or email as configured)"
    )
    reporter: Optional[str] = Field(None, description="Reporter of the issue (optional)")
    sentiment_score: Optional[float] = Field(
        None, description="Sentiment score from analysis (0.0-1.0)", ge=0.0, le=1.0
    )
    priority_score: Optional[int] = Field(None, description="Priority score from analysis (1-100)", ge=1, le=100)
    canny_post_url: Optional[str] = Field(None, description="URL to the original Canny.io post")


class GetIssueInput(BaseModel):
    """Input schema for GetIssueTool."""

    issue_key: str = Field(..., description="Jira issue key (e.g., 'PROJ-123')")
    fields: Optional[str] = Field(
        None,
        description="Optional comma-separated list of fields to return (e.g., 'summary,status,assignee'). Defaults to essential fields.",
    )


class UpdateIssueInput(BaseModel):
    """Input schema for UpdateIssueTool."""

    issue_key: str = Field(..., description="Jira issue key (e.g., 'PROJ-123')")
    fields: Optional[dict] = Field(
        None, description="Dictionary of fields to update (e.g., {'summary': 'New title', 'assignee': 'user@example.com'})"
    )
    additional_fields: Optional[dict] = Field(
        None,
        description="Additional fields dictionary for complex updates (e.g., {'priority': {'name': 'High'}, 'labels': ['urgent']})",
    )


class SearchIssuesInput(BaseModel):
    """Input schema for SearchIssuesTool."""

    jql: str = Field(..., description="JQL query string (e.g., 'project = PROJ AND status = Open')")
    limit: int = Field(50, ge=1, le=100, description="Maximum number of results (1-100, default 50)")
    fields: Optional[str] = Field(
        None,
        description="Optional comma-separated list of fields to return (e.g., 'summary,status,assignee'). Defaults to essential fields.",
    )


class AddCommentInput(BaseModel):
    """Input schema for AddCommentTool."""

    issue_key: str = Field(..., description="Jira issue key (e.g., 'PROJ-123')")
    comment: str = Field(..., min_length=1, description="Comment text (Markdown format supported)")


class TransitionIssueInput(BaseModel):
    """Input schema for TransitionIssueTool."""

    issue_key: str = Field(..., description="Jira issue key (e.g., 'PROJ-123')")
    transition_id: str = Field(..., description="ID of the transition to perform")
    comment: Optional[str] = Field(None, description="Optional comment for the transition")
    fields: Optional[dict] = Field(
        None, description="Optional dictionary of fields to update during transition (e.g., {'resolution': {'name': 'Fixed'}})"
    )


def create_create_issue_tool(jira_client: MCPJiraClient) -> BaseTool:
    """
    Create a LangChain tool for creating Jira issues.

    Args:
        jira_client: Initialized MCPJiraClient instance.

    Returns:
        LangChain StructuredTool for creating issues.
    """

    async def create_issue(
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        priority: str = "Medium",
        labels: List[str] = None,
        assignee: Optional[str] = None,
        reporter: Optional[str] = None,
        sentiment_score: Optional[float] = None,
        priority_score: Optional[int] = None,
        canny_post_url: Optional[str] = None,
    ) -> dict:
        """
        Create a new Jira issue from feedback analysis.

        Args:
            project_key: Jira project key (e.g., 'PROJ').
            summary: Summary/title of the Jira issue.
            description: Rich description including feedback context.
            issue_type: Jira issue type (Bug, Story, Task, etc.).
            priority: Priority level (Critical, High, Medium, Low).
            labels: Labels/tags to apply in Jira.
            assignee: User to assign the ticket to.
            reporter: Reporter of the issue.
            sentiment_score: Sentiment score from analysis (0.0-1.0).
            priority_score: Priority score from analysis (1-100).
            canny_post_url: URL to the original Canny.io post.

        Returns:
            JiraTicket dictionary (serialized model) representing the created issue.
        """
        try:
            ticket_data = JiraTicketCreate(
                project_key=project_key,
                summary=summary,
                description=description,
                issue_type=issue_type,
                priority=priority,
                labels=labels or [],
                assignee=assignee,
                reporter=reporter,
                sentiment_score=sentiment_score,
                priority_score=priority_score,
                canny_post_url=canny_post_url,
            )

            ticket = await jira_client.create_issue(ticket_data)
            return ticket.model_dump(mode="json")

        except MCPJiraError as e:
            logger.error(
                f"Failed to create Jira issue: {str(e)}",
                extra={"tool_name": e.tool_name, "project_key": project_key},
            )
            return {"error": str(e), "tool_name": e.tool_name}

        except Exception as e:
            logger.error(f"Unexpected error creating Jira issue: {str(e)}", exc_info=True)
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "create_jira_issue",
        args_schema=CreateIssueInput,
        return_direct=True,
    )(create_issue)

    decorated_tool.description = (
        "Create a new Jira issue from analyzed feedback. "
        "Use this to automatically create tickets for high-priority bugs or feature requests. "
        "The tool will format the ticket with all relevant analysis results including sentiment, "
        "priority score, and link back to the original Canny.io feedback post."
    )

    return decorated_tool


def create_get_issue_tool(jira_client: MCPJiraClient) -> BaseTool:
    """
    Create a LangChain tool for getting Jira issue details.

    Args:
        jira_client: Initialized MCPJiraClient instance.

    Returns:
        LangChain StructuredTool for getting issue details.
    """

    async def get_issue(issue_key: str, fields: Optional[str] = None) -> dict:
        """
        Retrieve detailed information for a specific Jira issue.

        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123').
            fields: Optional comma-separated list of fields to return.

        Returns:
            JiraTicket dictionary (serialized model) with issue details.
        """
        try:
            ticket = await jira_client.get_issue(issue_key, fields=fields)
            return ticket.model_dump(mode="json")

        except MCPJiraError as e:
            logger.error(
                f"Failed to get Jira issue {issue_key}: {str(e)}",
                extra={"tool_name": e.tool_name, "issue_key": issue_key},
            )
            return {"error": str(e), "tool_name": e.tool_name}

        except Exception as e:
            logger.error(
                f"Unexpected error getting Jira issue {issue_key}: {str(e)}",
                extra={"issue_key": issue_key},
                exc_info=True,
            )
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "get_jira_issue",
        args_schema=GetIssueInput,
        return_direct=True,
    )(get_issue)

    decorated_tool.description = (
        "Retrieve detailed information for a specific Jira issue. "
        "Use this to check ticket status, get updates, or verify ticket details. "
        "Essential for monitoring ticket resolution status."
    )

    return decorated_tool


def create_update_issue_tool(jira_client: MCPJiraClient) -> BaseTool:
    """
    Create a LangChain tool for updating Jira issues.

    Args:
        jira_client: Initialized MCPJiraClient instance.

    Returns:
        LangChain StructuredTool for updating issues.
    """

    async def update_issue(
        issue_key: str,
        fields: Optional[dict] = None,
        additional_fields: Optional[dict] = None,
    ) -> dict:
        """
        Update a Jira issue with new information.

        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123').
            fields: Dictionary of fields to update (e.g., {'summary': 'New title'}).
            additional_fields: Additional fields for complex updates (e.g., {'priority': {'name': 'High'}}).

        Returns:
            Updated JiraTicket dictionary (serialized model).
        """
        try:
            ticket = await jira_client.update_issue(
                issue_key=issue_key,
                fields=fields,
                additional_fields=additional_fields,
            )
            return ticket.model_dump(mode="json")

        except MCPJiraError as e:
            logger.error(
                f"Failed to update Jira issue {issue_key}: {str(e)}",
                extra={"tool_name": e.tool_name, "issue_key": issue_key},
            )
            return {"error": str(e), "tool_name": e.tool_name}

        except Exception as e:
            logger.error(
                f"Unexpected error updating Jira issue {issue_key}: {str(e)}",
                extra={"issue_key": issue_key},
                exc_info=True,
            )
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "update_jira_issue",
        args_schema=UpdateIssueInput,
        return_direct=True,
    )(update_issue)

    decorated_tool.description = (
        "Update a Jira issue with new information. "
        "Use this to modify ticket details, change priority, update assignees, or add metadata. "
        "Essential for keeping tickets synchronized with feedback status changes."
    )

    return decorated_tool


def create_search_issues_tool(jira_client: MCPJiraClient) -> BaseTool:
    """
    Create a LangChain tool for searching Jira issues using JQL.

    Args:
        jira_client: Initialized MCPJiraClient instance.

    Returns:
        LangChain StructuredTool for searching issues.
    """

    async def search_issues(jql: str, limit: int = 50, fields: Optional[str] = None) -> List[dict]:
        """
        Search for Jira issues using JQL query.

        Args:
            jql: JQL query string (e.g., 'project = PROJ AND status = Open').
            limit: Maximum number of results (1-100, default 50).
            fields: Optional comma-separated list of fields to return.

        Returns:
            List of JiraTicket dictionaries (serialized models) matching the query.
        """
        try:
            tickets = await jira_client.search_issues(jql=jql, limit=limit, fields=fields)
            return [ticket.model_dump(mode="json") for ticket in tickets]

        except MCPJiraError as e:
            logger.error(
                f"Failed to search Jira issues: {str(e)}",
                extra={"tool_name": e.tool_name, "jql": jql},
            )
            return [{"error": str(e), "tool_name": e.tool_name}]

        except Exception as e:
            logger.error(f"Unexpected error searching Jira issues: {str(e)}", exc_info=True)
            return [{"error": f"Unexpected error: {str(e)}"}]

    decorated_tool = tool(
        "search_jira_issues",
        args_schema=SearchIssuesInput,
        return_direct=True,
    )(search_issues)

    decorated_tool.description = (
        "Search for Jira issues using JQL (Jira Query Language). "
        "Use this to find related issues, monitor ticket statuses, or retrieve multiple tickets. "
        "Essential for monitoring workflows and finding duplicate issues. "
        "Example queries: 'project = PROJ AND status = Open', "
        "'assignee = currentUser() AND updated >= -7d', "
        "'labels = urgent AND priority = High'"
    )

    return decorated_tool


def create_add_comment_tool(jira_client: MCPJiraClient) -> BaseTool:
    """
    Create a LangChain tool for adding comments to Jira issues.

    Args:
        jira_client: Initialized MCPJiraClient instance.

    Returns:
        LangChain StructuredTool for adding comments.
    """

    async def add_comment(issue_key: str, comment: str) -> dict:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123').
            comment: Comment text (Markdown format supported).

        Returns:
            Comment response dictionary from API.
        """
        try:
            response = await jira_client.add_comment(issue_key=issue_key, comment=comment)
            return response

        except MCPJiraError as e:
            logger.error(
                f"Failed to add comment to Jira issue {issue_key}: {str(e)}",
                extra={"tool_name": e.tool_name, "issue_key": issue_key},
            )
            return {"error": str(e), "tool_name": e.tool_name}

        except Exception as e:
            logger.error(
                f"Unexpected error adding comment to Jira issue {issue_key}: {str(e)}",
                extra={"issue_key": issue_key},
                exc_info=True,
            )
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "add_jira_comment",
        args_schema=AddCommentInput,
        return_direct=True,
    )(add_comment)

    decorated_tool.description = (
        "Add a comment to a Jira issue. "
        "Use this to provide updates, link to feedback posts, or add context to tickets. "
        "Supports Markdown formatting for rich text comments."
    )

    return decorated_tool


def create_transition_issue_tool(jira_client: MCPJiraClient) -> BaseTool:
    """
    Create a LangChain tool for transitioning Jira issues to new statuses.

    Args:
        jira_client: Initialized MCPJiraClient instance.

    Returns:
        LangChain StructuredTool for transitioning issues.
    """

    async def transition_issue(
        issue_key: str,
        transition_id: str,
        comment: Optional[str] = None,
        fields: Optional[dict] = None,
    ) -> dict:
        """
        Transition a Jira issue to a new status.

        Args:
            issue_key: Jira issue key (e.g., 'PROJ-123').
            transition_id: ID of the transition to perform.
            comment: Optional comment for the transition.
            fields: Optional dictionary of fields to update during transition.

        Returns:
            Updated JiraTicket dictionary (serialized model).
        """
        try:
            ticket = await jira_client.transition_issue(
                issue_key=issue_key,
                transition_id=transition_id,
                comment=comment,
                fields=fields,
            )
            return ticket.model_dump(mode="json")

        except MCPJiraError as e:
            logger.error(
                f"Failed to transition Jira issue {issue_key}: {str(e)}",
                extra={"tool_name": e.tool_name, "issue_key": issue_key, "transition_id": transition_id},
            )
            return {"error": str(e), "tool_name": e.tool_name}

        except Exception as e:
            logger.error(
                f"Unexpected error transitioning Jira issue {issue_key}: {str(e)}",
                extra={"issue_key": issue_key},
                exc_info=True,
            )
            return {"error": f"Unexpected error: {str(e)}"}

    decorated_tool = tool(
        "transition_jira_issue",
        args_schema=TransitionIssueInput,
        return_direct=True,
    )(transition_issue)

    decorated_tool.description = (
        "Transition a Jira issue to a new status (e.g., 'To Do' → 'In Progress' → 'Done'). "
        "Use this to update ticket workflow status when issues are resolved or progress is made. "
        "Requires the transition_id which can be obtained using get_issue with transitions expanded."
    )

    return decorated_tool


def get_jira_tools(jira_client: MCPJiraClient) -> List[BaseTool]:
    """
    Get all LangChain tools for MCP Jira integration.

    Args:
        jira_client: Initialized MCPJiraClient instance.

    Returns:
        List of LangChain BaseTool instances for Jira operations.
    """
    return [
        create_create_issue_tool(jira_client),
        create_get_issue_tool(jira_client),
        create_update_issue_tool(jira_client),
        create_search_issues_tool(jira_client),
        create_add_comment_tool(jira_client),
        create_transition_issue_tool(jira_client),
    ]


__all__ = [
    "CreateIssueInput",
    "GetIssueInput",
    "UpdateIssueInput",
    "SearchIssuesInput",
    "AddCommentInput",
    "TransitionIssueInput",
    "create_create_issue_tool",
    "create_get_issue_tool",
    "create_update_issue_tool",
    "create_search_issues_tool",
    "create_add_comment_tool",
    "create_transition_issue_tool",
    "get_jira_tools",
]

