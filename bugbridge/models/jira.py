"""Pydantic models for Jira ticket data"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class JiraTicket(BaseModel):
    """Model for Jira ticket information"""
    
    ticket_id: str = Field(..., description="Jira ticket ID")
    ticket_key: str = Field(..., description="Jira ticket key (e.g., BB-123)")
    project_key: str = Field(..., description="Jira project key")
    summary: str = Field(..., description="Ticket summary/title")
    description: str = Field(..., description="Ticket description")
    issue_type: str = Field(..., description="Issue type (Bug, Story, Task)")
    priority: str = Field(..., description="Jira priority (Critical, High, Medium, Low)")
    status: str = Field(..., description="Current ticket status")
    assignee: Optional[str] = Field(None, description="Assigned user")
    reporter: Optional[str] = Field(None, description="Reporter user")
    created_at: datetime = Field(..., description="Ticket creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    url: Optional[str] = Field(None, description="URL to Jira ticket")
    feedback_post_id: Optional[str] = Field(None, description="Linked Canny.io post ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "10001",
                "ticket_key": "BB-123",
                "project_key": "BB",
                "summary": "Fix login page loading issue on mobile",
                "description": "Customer reported login page not loading on mobile devices...",
                "issue_type": "Bug",
                "priority": "High",
                "status": "In Progress",
                "assignee": "john.doe",
                "reporter": "bugbridge.bot",
                "created_at": "2024-11-19T11:05:00Z",
                "updated_at": "2024-11-19T14:30:00Z",
                "resolved_at": None,
                "url": "https://bugbridge-sjsu.atlassian.net/browse/BB-123",
                "feedback_post_id": "691d7c0a58a681e83ef06510"
            }
        }


class JiraTicketCreate(BaseModel):
    """Model for creating a Jira ticket"""
    
    project_key: str = Field(..., description="Jira project key")
    summary: str = Field(..., description="Ticket summary/title")
    description: str = Field(..., description="Ticket description")
    issue_type: str = Field(default="Bug", description="Issue type")
    priority: str = Field(default="Medium", description="Priority level")
    labels: list[str] = Field(default_factory=list, description="Ticket labels")
    assignee: Optional[str] = Field(None, description="Assigned user")
