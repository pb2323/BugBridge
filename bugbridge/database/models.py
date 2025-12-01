"""
Database ORM Models

SQLAlchemy ORM models for persistent storage of feedback, analysis results, 
workflow state, and related data.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
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
    
    # Foreign key
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Bug detection results
    is_bug = Column(Boolean, nullable=True)
    bug_severity = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    
    # Sentiment analysis results
    sentiment = Column(String(50), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    urgency = Column(String(50), nullable=True)
    
    # Priority scoring results
    priority_score = Column(Integer, nullable=True, index=True)
    is_burning_issue = Column(Boolean, default=False, nullable=False)
    recommended_jira_priority = Column(String(50), nullable=True)
    
    # Additional analysis data (JSON)
    analysis_data = Column(JSON, nullable=True)
    
    # Timestamp
    analyzed_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    
    # Relationships
    feedback_post = relationship("FeedbackPost", back_populates="analysis_results")
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, feedback_post_id={self.feedback_post_id}, is_bug={self.is_bug}, priority_score={self.priority_score})>"


class JiraTicket(Base):
    """
    SQLAlchemy ORM model for Jira tickets created from feedback.
    """
    
    __tablename__ = "jira_tickets"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key (optional, ticket can exist without feedback)
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Jira identifiers
    jira_issue_key = Column(String(100), unique=True, nullable=False, index=True)
    jira_issue_id = Column(String(255), nullable=True)
    jira_project_key = Column(String(100), nullable=True, index=True)
    
    # Ticket metadata
    status = Column(String(100), nullable=True, index=True)
    priority = Column(String(50), nullable=True)
    assignee = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    
    # Relationships
    feedback_post = relationship("FeedbackPost", back_populates="jira_tickets")
    notifications = relationship("Notification", back_populates="jira_ticket")
    
    def __repr__(self):
        return f"<JiraTicket(id={self.id}, jira_issue_key={self.jira_issue_key}, status={self.status})>"


class WorkflowState(Base):
    """
    SQLAlchemy ORM model for storing LangGraph workflow state.
    """
    
    __tablename__ = "workflow_states"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign key
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Workflow metadata
    workflow_status = Column(String(100), nullable=False, index=True)
    workflow_id = Column(String(255), nullable=True, unique=True, index=True)
    
    # State data (JSON)
    state_data = Column(JSON, nullable=True)
    
    # Timestamp
    last_updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now(), index=True)
    
    # Relationships
    feedback_post = relationship("FeedbackPost", back_populates="workflow_states")
    
    def __repr__(self):
        return f"<WorkflowState(id={self.id}, feedback_post_id={self.feedback_post_id}, workflow_status={self.workflow_status})>"


class Notification(Base):
    """
    SQLAlchemy ORM model for customer notifications sent via Canny.io.
    """
    
    __tablename__ = "notifications"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Foreign keys
    feedback_post_id = Column(UUID(as_uuid=True), ForeignKey("feedback_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    jira_ticket_id = Column(UUID(as_uuid=True), ForeignKey("jira_tickets.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Notification metadata
    notification_type = Column(String(100), nullable=False)
    notification_status = Column(String(100), nullable=False, index=True)
    reply_content = Column(Text, nullable=True)
    
    # Timestamps
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    
    # Relationships
    feedback_post = relationship("FeedbackPost", back_populates="notifications")
    jira_ticket = relationship("JiraTicket", back_populates="notifications")
    
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


class User(Base):
    """
    SQLAlchemy ORM model for dashboard users.
    
    Stores user accounts for authentication and authorization.
    """
    
    __tablename__ = "users"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # User credentials
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # User role (admin or viewer)
    role = Column(String(50), nullable=False, default="viewer", index=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"
