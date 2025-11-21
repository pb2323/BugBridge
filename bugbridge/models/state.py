"""
Workflow State Model

TypedDict definition for LangGraph workflow state.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict

from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost


class BugBridgeState(TypedDict, total=False):
    """
    LangGraph workflow state for BugBridge feedback processing.
    
    This TypedDict defines the shared state structure used throughout
    the LangGraph workflow for processing feedback from Canny.io to Jira.
    
    Attributes:
        feedback_post: The feedback post from Canny.io
        bug_detection: Results from Bug Detection Agent
        sentiment_analysis: Results from Sentiment Analysis Agent
        priority_score: Results from Priority Scoring Agent
        jira_ticket_id: Jira issue key (e.g., "PROJ-123")
        jira_ticket_url: URL to the Jira ticket
        jira_ticket_status: Current status of the Jira ticket
        workflow_status: Current status in the workflow
        errors: List of error messages encountered during processing
        timestamps: Dictionary of timestamps for each workflow stage
        metadata: Additional metadata for workflow tracking
    """
    
    # Input
    feedback_post: Optional[FeedbackPost]
    
    # Analysis Results
    bug_detection: Optional[BugDetectionResult]
    sentiment_analysis: Optional[SentimentAnalysisResult]
    priority_score: Optional[PriorityScoreResult]
    
    # Jira Integration
    jira_ticket_id: Optional[str]
    jira_ticket_url: Optional[str]
    jira_ticket_status: Optional[str]
    
    # Workflow Status
    workflow_status: Optional[
        Literal[
            "collected",
            "analyzed",
            "ticket_created",
            "monitoring",
            "resolved",
            "notified",
            "completed",
            "failed"
        ]
    ]
    
    # Metadata
    errors: List[str]
    timestamps: Dict[str, datetime]
    metadata: Dict[str, Any]

