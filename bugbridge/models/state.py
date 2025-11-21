"""LangGraph workflow state model"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, TypedDict
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.analysis import (
    BugDetectionResult,
    SentimentAnalysisResult,
    PriorityScoreResult,
)


class BugBridgeState(TypedDict, total=False):
    """State model for LangGraph workflow
    
    This represents the shared state that flows through all agent nodes
    in the feedback processing workflow.
    """
    
    # Input - Feedback post to process
    feedback_post: Optional[FeedbackPost]
    
    # Analysis Results - Output from AI agents
    bug_detection: Optional[BugDetectionResult]
    sentiment_analysis: Optional[SentimentAnalysisResult]
    priority_score: Optional[PriorityScoreResult]
    
    # Jira Integration - Ticket information
    jira_ticket_id: Optional[str]
    jira_ticket_key: Optional[str]
    jira_ticket_url: Optional[str]
    jira_ticket_status: Optional[str]
    
    # Workflow Status - Current processing stage
    workflow_status: Literal[
        "collected",
        "analyzed",
        "ticket_created",
        "monitoring",
        "resolved",
        "notified",
        "completed",
        "failed"
    ]
    
    # Metadata - Error tracking and timestamps
    errors: List[str]
    timestamps: Dict[str, datetime]
    metadata: Dict[str, Any]
