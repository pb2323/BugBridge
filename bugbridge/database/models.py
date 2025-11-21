"""SQLAlchemy ORM models for database"""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid

Base = declarative_base()


def generate_uuid():
    """Generate UUID string"""
    return str(uuid.uuid4())


class FeedbackPostDB(Base):
    """Database model for feedback posts"""
    __tablename__ = "feedback_posts"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    canny_post_id = Column(String(255), unique=True, nullable=False, index=True)
    board_id = Column(String(255), nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(String(255))
    author_name = Column(String(255))
    votes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    status = Column(String(100))
    url = Column(Text)
    tags = Column(JSON)  # Store as JSON array
    collected_at = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    analysis = relationship("AnalysisResultDB", back_populates="feedback_post", uselist=False)
    jira_ticket = relationship("JiraTicketDB", back_populates="feedback_post", uselist=False)
    workflow_state = relationship("WorkflowStateDB", back_populates="feedback_post", uselist=False)
    notifications = relationship("NotificationDB", back_populates="feedback_post")


class AnalysisResultDB(Base):
    """Database model for analysis results"""
    __tablename__ = "analysis_results"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    feedback_post_id = Column(String(36), ForeignKey("feedback_posts.id"), nullable=False)
    
    # Bug Detection
    is_bug = Column(Boolean)
    bug_severity = Column(String(50))
    confidence = Column(Float)
    
    # Sentiment Analysis
    sentiment = Column(String(50))
    sentiment_score = Column(Float)
    urgency = Column(String(50))
    
    # Priority Scoring
    priority_score = Column(Integer)
    is_burning_issue = Column(Boolean)
    
    # Full analysis data stored as JSON
    analysis_data = Column(JSON)
    analyzed_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    feedback_post = relationship("FeedbackPostDB", back_populates="analysis")


class JiraTicketDB(Base):
    """Database model for Jira tickets"""
    __tablename__ = "jira_tickets"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    feedback_post_id = Column(String(36), ForeignKey("feedback_posts.id"), nullable=False)
    jira_issue_key = Column(String(100), unique=True, nullable=False, index=True)
    jira_issue_id = Column(String(255))
    jira_project_key = Column(String(100))
    status = Column(String(100), index=True)
    priority = Column(String(50))
    assignee = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)
    resolved_at = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    feedback_post = relationship("FeedbackPostDB", back_populates="jira_ticket")
    notifications = relationship("NotificationDB", back_populates="jira_ticket")


class WorkflowStateDB(Base):
    """Database model for workflow state"""
    __tablename__ = "workflow_states"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    feedback_post_id = Column(String(36), ForeignKey("feedback_posts.id"), nullable=False)
    workflow_status = Column(String(100), index=True)
    state_data = Column(JSON)  # Store full state as JSON
    last_updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    feedback_post = relationship("FeedbackPostDB", back_populates="workflow_state")


class NotificationDB(Base):
    """Database model for notifications"""
    __tablename__ = "notifications"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    feedback_post_id = Column(String(36), ForeignKey("feedback_posts.id"), nullable=False)
    jira_ticket_id = Column(String(36), ForeignKey("jira_tickets.id"))
    notification_type = Column(String(100))
    notification_status = Column(String(100))
    reply_content = Column(Text)
    sent_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)
    
    # Relationships
    feedback_post = relationship("FeedbackPostDB", back_populates="notifications")
    jira_ticket = relationship("JiraTicketDB", back_populates="notifications")


class ReportDB(Base):
    """Database model for reports"""
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    report_type = Column(String(100))
    report_date = Column(DateTime)
    report_content = Column(Text)
    metrics = Column(JSON)  # Store metrics as JSON
    generated_at = Column(DateTime, default=datetime.now)
