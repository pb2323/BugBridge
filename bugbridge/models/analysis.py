"""
Analysis Result Models

Pydantic models for AI agent analysis results (bug detection, sentiment analysis, priority scoring).
"""

from datetime import datetime
from typing import List, Literal
from pydantic import BaseModel, Field


class BugDetectionResult(BaseModel):
    """
    Result of bug detection analysis from Bug Detection Agent.
    
    Attributes:
        is_bug: Whether the feedback describes a bug (True) or feature request (False)
        confidence: Confidence score for the classification (0.0 to 1.0)
        bug_severity: Severity of the bug if detected (Critical, High, Medium, Low, or N/A)
        keywords_identified: List of keywords that triggered bug detection
        reasoning: Explanation of why this classification was made
        analyzed_at: Timestamp when the analysis was performed
    """
    
    is_bug: bool = Field(..., description="Whether the feedback describes a bug or feature request")
    confidence: float = Field(..., description="Confidence score for the classification", ge=0.0, le=1.0)
    bug_severity: Literal["Critical", "High", "Medium", "Low", "N/A"] = Field(
        ..., description="Severity of the bug if detected, or N/A if not a bug"
    )
    keywords_identified: List[str] = Field(
        default_factory=list,
        description="List of keywords that triggered bug detection (e.g., 'bug', 'broken', 'error', 'not working')"
    )
    reasoning: str = Field(..., description="Explanation of why this classification was made", min_length=10)
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the bug detection analysis was performed"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "is_bug": True,
                "confidence": 0.92,
                "bug_severity": "High",
                "keywords_identified": ["error", "broken", "not working", "bug"],
                "reasoning": "The feedback describes a payment processing error where transactions fail to complete. This indicates a critical functionality issue that prevents users from completing core workflows.",
                "analyzed_at": "2025-11-20T16:05:00Z"
            }
        }


class SentimentAnalysisResult(BaseModel):
    """
    Result of sentiment analysis from Sentiment Analysis Agent.
    
    Attributes:
        sentiment: Overall sentiment classification
        sentiment_score: Sentiment intensity score (0.0 = very negative, 1.0 = very positive)
        urgency: Urgency level detected in the language
        emotions_detected: List of specific emotions detected in the text
        reasoning: Explanation of the sentiment analysis
        analyzed_at: Timestamp when the sentiment analysis was performed
    """
    
    sentiment: Literal["Positive", "Neutral", "Negative", "Frustrated", "Angry"] = Field(
        ..., description="Overall sentiment classification of the feedback"
    )
    sentiment_score: float = Field(
        ...,
        description="Sentiment intensity score (0.0 = very negative, 1.0 = very positive)",
        ge=0.0,
        le=1.0
    )
    urgency: Literal["High", "Medium", "Low"] = Field(..., description="Urgency level detected in the language")
    emotions_detected: List[str] = Field(
        default_factory=list,
        description="List of specific emotions detected (e.g., 'frustrated', 'hopeful', 'excited', 'disappointed')"
    )
    reasoning: str = Field(..., description="Explanation of the sentiment analysis", min_length=10)
    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the sentiment analysis was performed"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "sentiment": "Frustrated",
                "sentiment_score": 0.25,
                "urgency": "High",
                "emotions_detected": ["frustrated", "disappointed", "concerned"],
                "reasoning": "The user expresses strong frustration about a recurring issue that impacts their daily workflow. Multiple urgent language indicators are present such as 'urgent', 'critical', and 'blocking'.",
                "analyzed_at": "2025-11-20T16:05:30Z"
            }
        }


class PriorityScoreResult(BaseModel):
    """
    Result of priority scoring from Priority Scoring Agent.
    
    Attributes:
        priority_score: Priority score from 1 to 100 (higher = more important)
        is_burning_issue: Whether this is flagged as a burning issue requiring immediate attention
        priority_reasoning: Explanation of how the priority score was calculated
        recommended_jira_priority: Recommended Jira priority level based on the score
        engagement_score: Calculated engagement score based on votes and comments
        sentiment_weight: Weight given to sentiment in the priority calculation
        bug_severity_weight: Weight given to bug severity in the priority calculation
        calculated_at: Timestamp when the priority score was calculated
    """
    
    priority_score: int = Field(..., description="Priority score from 1 to 100 (higher = more important)", ge=1, le=100)
    is_burning_issue: bool = Field(
        False,
        description="Whether this is flagged as a burning issue requiring immediate attention"
    )
    priority_reasoning: str = Field(..., description="Explanation of how the priority score was calculated", min_length=10)
    recommended_jira_priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        ..., description="Recommended Jira priority level based on the score"
    )
    engagement_score: float = Field(
        ..., description="Calculated engagement score based on votes and comments", ge=0.0
    )
    sentiment_weight: float = Field(..., description="Weight given to sentiment in the priority calculation", ge=0.0, le=1.0)
    bug_severity_weight: float = Field(
        ..., description="Weight given to bug severity in the priority calculation", ge=0.0, le=1.0
    )
    calculated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the priority score was calculated"
    )
    
    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "priority_score": 85,
                "is_burning_issue": True,
                "priority_reasoning": "High priority due to combination of critical bug severity, high negative sentiment (frustrated), strong user engagement (45 votes, 12 comments), and business impact keywords. This is a blocking issue affecting multiple users.",
                "recommended_jira_priority": "Critical",
                "engagement_score": 0.75,
                "sentiment_weight": 0.3,
                "bug_severity_weight": 0.4,
                "calculated_at": "2025-11-20T16:06:00Z"
            }
        }

