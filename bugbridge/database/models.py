"""
Database ORM Models

SQLAlchemy ORM models for persistent storage of feedback, analysis results, 
workflow state, and related data.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class FeedbackPost(Base):
    """
    SQLAlchemy ORM model for feedback posts from Canny.io.
    
    Corresponds to the Pydantic FeedbackPost model.
    """
    
    __tablename__ = "feedback_posts"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Canny.io identifiers
    canny_post_id = Column(String(255), unique=True, nullable=False, index=True)
    board_id = Column(String(255), nullable=False, index=True)
    
    # Post content
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    
    # Author information
    author_id = Column(String(255), nullable=True)
    author_name = Column(String(255), nullable=True)
    
    # Engagement metrics
    votes = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    
    # Post metadata
    status = Column(String(100), nullable=True)
    url = Column(Text, nullable=True)
    tags = Column(ARRAY(String), nullable=True, default=[])
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    collected_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Relationships
    analysis_results = relationship("AnalysisResult", back_populates="feedback_post", cascade="all, delete-orphan")
    jira_tickets = relationship("JiraTicket", back_populates="feedback_post", cascade="all, delete-orphan")
    workflow_states = relationship("WorkflowState", back_populates="feedback_post", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="feedback_post", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<FeedbackPost(id={self.id}, canny_post_id={self.canny_post_id}, title={self.title[:50]}...)>"


class AnalysisResult(Base):
    """
    SQLAlchemy ORM model for AI agent analysis results.
    
    Stores bug detection, sentiment analysis, and priority scoring results.
    """
    
    __tablename__ = "analysis_results"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to feedback post
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id"), nullable=False, index=True)
    
    # Bug detection results
    is_bug = Column(Boolean, nullable=True)
    bug_severity = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Sentiment analysis results
    sentiment = Column(String(50), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    urgency = Column(String(50), nullable=True)
    
    # Priority scoring results
    priority_score = Column(Integer, nullable=True)
    is_burning_issue = Column(Boolean, default=False, nullable=False)
    
    # Full analysis data as JSON
    analysis_data = Column(JSON, nullable=True)
    
    # Timestamp
    analyzed_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Relationship
    feedback_post = relationship("FeedbackPost", back_populates="analysis_results")
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, feedback_post_id={self.feedback_post_id}, priority_score={self.priority_score})>"


class JiraTicket(Base):
    """
    SQLAlchemy ORM model for Jira tickets linked to feedback posts.
    """
    
    __tablename__ = "jira_tickets"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to feedback post
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id"), nullable=True, index=True)
    
    # Jira identifiers
    jira_issue_key = Column(String(100), unique=True, nullable=False, index=True)
    jira_issue_id = Column(String(255), nullable=True)
    jira_project_key = Column(String(100), nullable=False)
    
    # Ticket metadata
    status = Column(String(100), nullable=True, index=True)
    priority = Column(String(50), nullable=True)
    assignee = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationship
    feedback_post = relationship("FeedbackPost", back_populates="jira_tickets")
    
    def __repr__(self):
        return f"<JiraTicket(id={self.id}, jira_issue_key={self.jira_issue_key}, status={self.status})>"


class WorkflowState(Base):
    """
    SQLAlchemy ORM model for tracking workflow state for each feedback post.
    """
    
    __tablename__ = "workflow_states"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key to feedback post
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id"), nullable=False, index=True)
    
    # Workflow status
    workflow_status = Column(String(100), nullable=False, index=True)
    
    # State data as JSON
    state_data = Column(JSON, nullable=True)
    
    # Timestamp
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now(), index=True)
    
    # Relationship
    feedback_post = relationship("FeedbackPost", back_populates="workflow_states")
    
    def __repr__(self):
        return f"<WorkflowState(id={self.id}, feedback_post_id={self.feedback_post_id}, workflow_status={self.workflow_status})>"


class Notification(Base):
    """
    SQLAlchemy ORM model for tracking customer notifications.
    """
    
    __tablename__ = "notifications"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id"), nullable=False, index=True)
    jira_ticket_id = Column(UUID(as_uuid=True), ForeignKey("jira_tickets.id"), nullable=True, index=True)
    
    # Notification metadata
    notification_type = Column(String(100), nullable=False)
    notification_status = Column(String(100), nullable=False, index=True)
    reply_content = Column(Text, nullable=True)
    
    # Timestamps
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    feedback_post = relationship("FeedbackPost", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.id}, feedback_post_id={self.feedback_post_id}, notification_status={self.notification_status})>"


class Report(Base):
    """
    SQLAlchemy ORM model for storing generated reports.
    """
    
    __tablename__ = "reports"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Report metadata
    report_type = Column(String(100), nullable=False, index=True)
    report_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Report content
    report_content = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    
    # Timestamp
    generated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    def __repr__(self):
        return f"<Report(id={self.id}, report_type={self.report_type}, report_date={self.report_date})>"

