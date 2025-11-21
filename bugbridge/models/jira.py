"""
Jira Models

Pydantic models representing Jira tickets and related metadata.
"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class JiraTicketCreate(BaseModel):
    """
    Payload for creating Jira tickets via the Jira Creation Agent.

    Attributes:
        project_key: Jira project key (e.g., "PROJ")
        summary: Summary/title of the Jira issue
        description: Rich description including feedback context
        issue_type: Jira issue type (Bug, Story, Task, etc.)
        priority: Priority level mapped from priority score
        labels: List of labels/tags to apply in Jira
        assignee: User to assign the ticket to (optional)
        reporter: Reporter of the issue (optional, defaults to integration user)
        sentiment_score: Sentiment score from analysis (0.0-1.0)
        priority_score: Priority score (1-100)
        canny_post_url: URL to the original Canny.io post
        metadata: Additional metadata (e.g., sentiment reasoning, business impact)
    """

    project_key: str = Field(..., description="Jira project key (e.g., 'PROJ')")
    summary: str = Field(..., description="Summary/title of the Jira issue", min_length=1, max_length=255)
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
    priority_score: Optional[int] = Field(
        None, description="Priority score from analysis (1-100)", ge=1, le=100
    )
    canny_post_url: Optional[HttpUrl] = Field(None, description="URL to the original Canny.io post")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional metadata for Jira ticket")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "project_key": "BB",
                "summary": "[Bug] Payment processing fails with timeout error",
                "description": "The following feedback post reported a payment processing failure:\n\n"
                "- **Author:** John Doe\n"
                "- **Sentiment:** Frustrated (score: 0.2)\n"
                "- **Priority Score:** 88 (Burning issue)\n\n"
                "Users cannot complete payments due to a timeout error when submitting the transaction form.",
                "issue_type": "Bug",
                "priority": "Critical",
                "labels": ["feedback", "payment", "urgent"],
                "assignee": "jira.user@example.com",
                "reporter": "bugbridge.bot@example.com",
                "sentiment_score": 0.2,
                "priority_score": 88,
                "canny_post_url": "https://bugbridge.canny.io/admin/board/feedback/p/payment-processing-timeout",
                "metadata": {
                    "burning_issue": True,
                    "engagement": {"votes": 34, "comments": 12},
                },
            }
        }


class JiraTicket(BaseModel):
    """
    Representation of a Jira ticket stored by BugBridge.

    Attributes:
        id: Jira issue ID (numeric/string)
        key: Jira issue key (e.g., "PROJ-123")
        project_key: Jira project key
        issue_type: Issue type (Bug, Story, Task, etc.)
        priority: Priority level (Critical, High, Medium, Low)
        status: Current status (e.g., "To Do", "In Progress", "Done")
        summary: Summary/title of the issue
        description: Description text
        labels: Labels/tags applied to the issue
        assignee: Current assignee (display name or account ID)
        reporter: Reporter of the issue
        linked_feedback_post_id: ID of the linked feedback post (BugBridge internal)
        canny_post_url: URL to the original Canny.io post
        sentiment_score: Sentiment score from analysis
        priority_score: Priority score from analysis
        created_at: When the Jira ticket was created
        updated_at: When the ticket was last updated
        resolved_at: When the ticket was resolved (if applicable)
        url: URL to the Jira issue in the browser
    """

    id: Optional[str] = Field(None, description="Jira issue ID")
    key: str = Field(..., description="Jira issue key (e.g., 'PROJ-123')")
    project_key: str = Field(..., description="Jira project key")
    issue_type: Literal["Bug", "Story", "Task", "Epic", "Incident", "Service Request", "Sub-task"] = Field(
        "Bug", description="Jira issue type"
    )
    priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        "Medium", description="Priority level"
    )
    status: str = Field(..., description="Current status (e.g., 'To Do', 'In Progress', 'Done')")
    summary: str = Field(..., description="Summary/title of the issue")
    description: Optional[str] = Field(None, description="Description text")
    labels: List[str] = Field(default_factory=list, description="Labels/tags applied to the issue")
    assignee: Optional[str] = Field(None, description="Current assignee (display name or account ID)")
    reporter: Optional[str] = Field(None, description="Reporter of the issue")
    linked_feedback_post_id: Optional[str] = Field(
        None, description="ID of the linked feedback post (BugBridge internal ID)"
    )
    canny_post_url: Optional[HttpUrl] = Field(None, description="URL to the original Canny.io post")
    sentiment_score: Optional[float] = Field(None, description="Sentiment score from analysis", ge=0.0, le=1.0)
    priority_score: Optional[int] = Field(None, description="Priority score from analysis", ge=1, le=100)
    created_at: datetime = Field(..., description="Timestamp when Jira ticket was created")
    updated_at: datetime = Field(..., description="Timestamp when Jira ticket was last updated")
    resolved_at: Optional[datetime] = Field(None, description="Timestamp when Jira ticket was resolved")
    url: Optional[HttpUrl] = Field(None, description="Browser URL to the Jira issue")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "100123",
                "key": "BB-143",
                "project_key": "BB",
                "issue_type": "Bug",
                "priority": "Critical",
                "status": "In Progress",
                "summary": "[Bug] Payment processing fails with timeout error",
                "description": "Automatically created from Canny feedback post ...",
                "labels": ["feedback", "payment", "urgent"],
                "assignee": "Alice Johnson",
                "reporter": "BugBridge Automation",
                "linked_feedback_post_id": "651a1b2c3d4e5f6g7h8i9j0k",
                "canny_post_url": "https://bugbridge.canny.io/admin/board/feedback/p/payment-processing-timeout",
                "sentiment_score": 0.2,
                "priority_score": 88,
                "created_at": "2025-11-20T16:07:00Z",
                "updated_at": "2025-11-21T09:15:00Z",
                "resolved_at": None,
                "url": "https://jira.company.com/browse/BB-143",
            }
        }


class JiraStatusHistoryEntry(BaseModel):
    """
    Represents a single status change entry for a Jira ticket.

    Attributes:
        status_from: Status before the transition
        status_to: Status after the transition
        changed_at: Timestamp when the status change occurred
        changed_by: User who made the change
        comment: Optional comment/context for the change
    """

    status_from: Optional[str] = Field(None, description="Status before the transition")
    status_to: str = Field(..., description="Status after the transition")
    changed_at: datetime = Field(..., description="Timestamp when the status change occurred")
    changed_by: Optional[str] = Field(None, description="User who made the change")
    comment: Optional[str] = Field(None, description="Optional comment/context for the change")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "status_from": "In Progress",
                "status_to": "Done",
                "changed_at": "2025-11-22T11:30:00Z",
                "changed_by": "Bob Smith",
                "comment": "Issue resolved and verified in staging environment.",
            }
        }


class JiraTicketLink(BaseModel):
    """
    Represents the bidirectional link between a feedback post and a Jira ticket.

    Attributes:
        feedback_post_id: ID of the feedback post (BugBridge internal ID)
        jira_ticket_key: Jira issue key (e.g., "PROJ-123")
        linked_at: Timestamp when the link was created
        link_type: Type of link (e.g., "creates", "relates_to", "duplicates")
    """

    feedback_post_id: str = Field(..., description="ID of the feedback post (BugBridge internal ID)")
    jira_ticket_key: str = Field(..., description="Jira issue key (e.g., 'PROJ-123')")
    linked_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the link was created")
    link_type: Literal["creates", "relates_to", "duplicates", "blocks", "is_blocked_by"] = Field(
        "creates", description="Type of link between feedback post and Jira ticket"
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "feedback_post_id": "651a1b2c3d4e5f6g7h8i9j0k",
                "jira_ticket_key": "BB-143",
                "linked_at": "2025-11-20T16:07:30Z",
                "link_type": "creates",
            }
        }

