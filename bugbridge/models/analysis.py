"""Pydantic models for AI analysis results"""

from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class BugDetectionResult(BaseModel):
    """Model for bug detection analysis result"""
    
    is_bug: bool = Field(..., description="Whether this is a bug report")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    bug_severity: Literal["Critical", "High", "Medium", "Low", "N/A"] = Field(
        ..., description="Bug severity level"
    )
    keywords_identified: List[str] = Field(
        default_factory=list, description="Keywords that triggered bug detection"
    )
    reasoning: str = Field(..., description="Reasoning for classification")
    analyzed_at: datetime = Field(
        default_factory=datetime.now, description="Analysis timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_bug": True,
                "confidence": 0.95,
                "bug_severity": "High",
                "keywords_identified": ["not loading", "error", "broken"],
                "reasoning": "User reports functionality not working with error messages",
                "analyzed_at": "2024-11-19T11:01:00Z"
            }
        }


class SentimentAnalysisResult(BaseModel):
    """Model for sentiment analysis result"""
    
    sentiment: Literal["Positive", "Neutral", "Negative", "Frustrated", "Angry"] = Field(
        ..., description="Sentiment classification"
    )
    sentiment_score: float = Field(
        ..., ge=0.0, le=1.0, description="Sentiment score (0=very negative, 1=very positive)"
    )
    urgency: Literal["High", "Medium", "Low"] = Field(..., description="Urgency level")
    emotions_detected: List[str] = Field(
        default_factory=list, description="Specific emotions identified"
    )
    reasoning: str = Field(..., description="Reasoning for sentiment analysis")
    analyzed_at: datetime = Field(
        default_factory=datetime.now, description="Analysis timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "sentiment": "Frustrated",
                "sentiment_score": 0.3,
                "urgency": "High",
                "emotions_detected": ["frustrated", "concerned"],
                "reasoning": "User expresses frustration about recurring issue",
                "analyzed_at": "2024-11-19T11:02:00Z"
            }
        }


class PriorityScoreResult(BaseModel):
    """Model for priority scoring result"""
    
    priority_score: int = Field(..., ge=1, le=100, description="Priority score (1-100)")
    is_burning_issue: bool = Field(..., description="Whether this requires immediate attention")
    priority_reasoning: str = Field(..., description="Reasoning for priority score")
    recommended_jira_priority: Literal["Critical", "High", "Medium", "Low"] = Field(
        ..., description="Recommended Jira priority level"
    )
    engagement_score: float = Field(..., description="User engagement score")
    sentiment_weight: float = Field(..., description="Sentiment contribution to priority")
    bug_severity_weight: float = Field(..., description="Bug severity contribution to priority")
    calculated_at: datetime = Field(
        default_factory=datetime.now, description="Calculation timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "priority_score": 85,
                "is_burning_issue": True,
                "priority_reasoning": "High user engagement with negative sentiment and critical bug",
                "recommended_jira_priority": "Critical",
                "engagement_score": 0.8,
                "sentiment_weight": 0.9,
                "bug_severity_weight": 0.95,
                "calculated_at": "2024-11-19T11:03:00Z"
            }
        }
