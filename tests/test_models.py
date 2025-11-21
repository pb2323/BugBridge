"""
Unit Tests for Pydantic Models

Tests for all Pydantic data models including validation, serialization, and edge cases.
"""

from datetime import datetime, timezone
from typing import Dict, Any

import pytest
from pydantic import ValidationError

from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.analysis import (
    BugDetectionResult,
    SentimentAnalysisResult,
    PriorityScoreResult,
)
from bugbridge.models.jira import (
    JiraTicketCreate,
    JiraTicket,
    JiraStatusHistoryEntry,
    JiraTicketLink,
)
from bugbridge.models.state import BugBridgeState


class TestFeedbackPost:
    """Tests for FeedbackPost model."""
    
    def test_feedback_post_creation(self):
        """Test creating a valid FeedbackPost."""
        post = FeedbackPost(
            post_id="test_post_123",
            board_id="board_456",
            title="Test Feedback Post",
            content="This is a test feedback post content",
            author_id="author_789",
            author_name="John Doe",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            votes=10,
            comments_count=5,
            status="open",
            url="https://bugbridge.canny.io/admin/board/feedback/p/test-post",
            tags=["bug", "ui"],
        )
        
        assert post.post_id == "test_post_123"
        assert post.board_id == "board_456"
        assert post.title == "Test Feedback Post"
        assert post.votes == 10
        assert post.comments_count == 5
        assert "bug" in post.tags
    
    def test_feedback_post_minimal(self):
        """Test creating FeedbackPost with minimal required fields."""
        post = FeedbackPost(
            post_id="minimal_post",
            board_id="board_1",
            title="Minimal Post",
            content="Content",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        assert post.post_id == "minimal_post"
        assert post.votes == 0  # Default value
        assert post.comments_count == 0  # Default value
        assert post.tags == []  # Default empty list
        assert post.collected_at is not None
    
    def test_feedback_post_validation_title_min_length(self):
        """Test that title must have at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            FeedbackPost(
                post_id="test",
                board_id="board",
                title="",  # Empty title should fail
                content="Content",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        
        # Check that validation error occurred
        errors = exc_info.value.errors()
        assert len(errors) > 0
        assert any("title" in str(error) and "at least 1 character" in str(error) for error in errors)
    
    def test_feedback_post_negative_votes(self):
        """Test that votes cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            FeedbackPost(
                post_id="test",
                board_id="board",
                title="Test",
                content="Content",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                votes=-1,  # Negative should fail
            )
        
        errors = exc_info.value.errors()
        assert any("greater than or equal to 0" in str(error) for error in errors)


class TestBugDetectionResult:
    """Tests for BugDetectionResult model."""
    
    def test_bug_detection_result_creation(self):
        """Test creating a valid BugDetectionResult."""
        result = BugDetectionResult(
            is_bug=True,
            confidence=0.92,
            bug_severity="High",
            keywords_identified=["error", "broken", "bug"],
            reasoning="The feedback describes a critical error in payment processing",
        )
        
        assert result.is_bug is True
        assert result.confidence == 0.92
        assert result.bug_severity == "High"
        assert "error" in result.keywords_identified
        assert result.analyzed_at is not None
    
    def test_bug_detection_result_not_bug(self):
        """Test BugDetectionResult for feature request."""
        result = BugDetectionResult(
            is_bug=False,
            confidence=0.85,
            bug_severity="N/A",
            keywords_identified=[],
            reasoning="This is a feature request, not a bug",
        )
        
        assert result.is_bug is False
        assert result.bug_severity == "N/A"
    
    def test_bug_detection_result_confidence_range(self):
        """Test that confidence must be between 0.0 and 1.0."""
        # Valid values
        BugDetectionResult(
            is_bug=True,
            confidence=0.0,
            bug_severity="Low",
            keywords_identified=[],
            reasoning="Test confidence range validation with valid values",
        )
        
        BugDetectionResult(
            is_bug=True,
            confidence=1.0,
            bug_severity="High",
            keywords_identified=[],
            reasoning="Test confidence range validation with maximum value",
        )
        
        # Invalid values
        with pytest.raises(ValidationError):
            BugDetectionResult(
                is_bug=True,
                confidence=1.5,  # Too high
                bug_severity="High",
                keywords_identified=[],
                reasoning="Test confidence range validation with invalid high value",
            )
        
        with pytest.raises(ValidationError):
            BugDetectionResult(
                is_bug=True,
                confidence=-0.1,  # Too low
                bug_severity="High",
                keywords_identified=[],
                reasoning="Test confidence range validation with invalid low value",
            )
    
    def test_bug_detection_result_reasoning_min_length(self):
        """Test that reasoning must have at least 10 characters."""
        with pytest.raises(ValidationError):
            BugDetectionResult(
                is_bug=True,
                confidence=0.9,
                bug_severity="High",
                keywords_identified=[],
                reasoning="Short",  # Too short
            )


class TestSentimentAnalysisResult:
    """Tests for SentimentAnalysisResult model."""
    
    def test_sentiment_analysis_result_creation(self):
        """Test creating a valid SentimentAnalysisResult."""
        result = SentimentAnalysisResult(
            sentiment="Frustrated",
            sentiment_score=0.25,
            urgency="High",
            emotions_detected=["frustrated", "disappointed"],
            reasoning="User expresses strong frustration about recurring issue",
        )
        
        assert result.sentiment == "Frustrated"
        assert result.sentiment_score == 0.25
        assert result.urgency == "High"
        assert "frustrated" in result.emotions_detected
    
    def test_sentiment_analysis_result_all_sentiments(self):
        """Test all valid sentiment values."""
        sentiments = ["Positive", "Neutral", "Negative", "Frustrated", "Angry"]
        
        for sentiment in sentiments:
            result = SentimentAnalysisResult(
                sentiment=sentiment,
                sentiment_score=0.5,
                urgency="Medium",
                emotions_detected=[],
                reasoning="Test sentiment analysis",
            )
            assert result.sentiment == sentiment
    
    def test_sentiment_analysis_result_score_range(self):
        """Test that sentiment_score must be between 0.0 and 1.0."""
        # Valid
        SentimentAnalysisResult(
            sentiment="Positive",
            sentiment_score=0.0,
            urgency="Low",
            emotions_detected=[],
            reasoning="Test sentiment score validation",
        )
        
        # Invalid
        with pytest.raises(ValidationError):
            SentimentAnalysisResult(
                sentiment="Positive",
                sentiment_score=1.5,  # Too high
                urgency="Low",
                emotions_detected=[],
                reasoning="Test sentiment score validation",
            )


class TestPriorityScoreResult:
    """Tests for PriorityScoreResult model."""
    
    def test_priority_score_result_creation(self):
        """Test creating a valid PriorityScoreResult."""
        result = PriorityScoreResult(
            priority_score=85,
            is_burning_issue=True,
            priority_reasoning="High priority due to critical bug and strong user engagement",
            recommended_jira_priority="Critical",
            engagement_score=0.75,
            sentiment_weight=0.3,
            bug_severity_weight=0.4,
        )
        
        assert result.priority_score == 85
        assert result.is_burning_issue is True
        assert result.recommended_jira_priority == "Critical"
        assert result.engagement_score == 0.75
    
    def test_priority_score_result_range(self):
        """Test that priority_score must be between 1 and 100."""
        # Valid boundaries
        PriorityScoreResult(
            priority_score=1,
            priority_reasoning="Minimum priority score test",
            recommended_jira_priority="Low",
            engagement_score=0.0,
            sentiment_weight=0.0,
            bug_severity_weight=0.0,
        )
        
        PriorityScoreResult(
            priority_score=100,
            priority_reasoning="Maximum priority score test",
            recommended_jira_priority="Critical",
            engagement_score=1.0,
            sentiment_weight=1.0,
            bug_severity_weight=1.0,
        )
        
        # Invalid
        with pytest.raises(ValidationError):
            PriorityScoreResult(
                priority_score=0,  # Too low
                priority_reasoning="Test",
                recommended_jira_priority="Low",
                engagement_score=0.0,
                sentiment_weight=0.0,
                bug_severity_weight=0.0,
            )
        
        with pytest.raises(ValidationError):
            PriorityScoreResult(
                priority_score=101,  # Too high
                priority_reasoning="Test",
                recommended_jira_priority="Critical",
                engagement_score=1.0,
                sentiment_weight=1.0,
                bug_severity_weight=1.0,
            )
    
    def test_priority_score_result_weights(self):
        """Test weight validation (0.0 to 1.0)."""
        with pytest.raises(ValidationError):
            PriorityScoreResult(
                priority_score=50,
                priority_reasoning="Test weight validation",
                recommended_jira_priority="Medium",
                engagement_score=0.5,
                sentiment_weight=-0.1,  # Invalid
                bug_severity_weight=0.5,
            )


class TestJiraTicketCreate:
    """Tests for JiraTicketCreate model."""
    
    def test_jira_ticket_create_creation(self):
        """Test creating a valid JiraTicketCreate."""
        ticket = JiraTicketCreate(
            project_key="PROJ",
            summary="Fix payment processing bug",
            description="Detailed description of the bug",
            issue_type="Bug",
            priority="Critical",
            labels=["bug", "payment", "urgent"],
            sentiment_score=0.2,
            priority_score=88,
        )
        
        assert ticket.project_key == "PROJ"
        assert ticket.summary == "Fix payment processing bug"
        assert ticket.issue_type == "Bug"
        assert ticket.priority == "Critical"
        assert "bug" in ticket.labels
    
    def test_jira_ticket_create_defaults(self):
        """Test JiraTicketCreate with default values."""
        ticket = JiraTicketCreate(
            project_key="PROJ",
            summary="Test ticket",
            description="Description",
        )
        
        assert ticket.issue_type == "Bug"  # Default
        assert ticket.priority == "Medium"  # Default
        assert ticket.labels == []  # Default empty list


class TestJiraTicket:
    """Tests for JiraTicket model."""
    
    def test_jira_ticket_creation(self):
        """Test creating a valid JiraTicket."""
        ticket = JiraTicket(
            key="PROJ-123",
            project_key="PROJ",
            status="In Progress",
            summary="Test Jira ticket",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        assert ticket.key == "PROJ-123"
        assert ticket.project_key == "PROJ"
        assert ticket.status == "In Progress"


class TestJiraStatusHistoryEntry:
    """Tests for JiraStatusHistoryEntry model."""
    
    def test_jira_status_history_entry_creation(self):
        """Test creating a valid JiraStatusHistoryEntry."""
        entry = JiraStatusHistoryEntry(
            status_from="To Do",
            status_to="In Progress",
            changed_at=datetime.now(timezone.utc),
            changed_by="John Doe",
            comment="Starting work on this ticket",
        )
        
        assert entry.status_from == "To Do"
        assert entry.status_to == "In Progress"
        assert entry.changed_by == "John Doe"


class TestJiraTicketLink:
    """Tests for JiraTicketLink model."""
    
    def test_jira_ticket_link_creation(self):
        """Test creating a valid JiraTicketLink."""
        link = JiraTicketLink(
            feedback_post_id="post_123",
            jira_ticket_key="PROJ-456",
            link_type="creates",
        )
        
        assert link.feedback_post_id == "post_123"
        assert link.jira_ticket_key == "PROJ-456"
        assert link.link_type == "creates"
        assert link.linked_at is not None


class TestBugBridgeState:
    """Tests for BugBridgeState TypedDict."""
    
    def test_bug_bridge_state_creation(self):
        """Test creating a valid BugBridgeState."""
        state: BugBridgeState = {
            "feedback_post": None,
            "bug_detection": None,
            "sentiment_analysis": None,
            "priority_score": None,
            "jira_ticket_id": None,
            "jira_ticket_url": None,
            "jira_ticket_status": None,
            "workflow_status": "collected",
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }
        
        assert state["workflow_status"] == "collected"
        assert state["errors"] == []
        assert state["timestamps"] == {}
    
    def test_bug_bridge_state_with_data(self):
        """Test BugBridgeState with actual data."""
        from bugbridge.models.feedback import FeedbackPost
        
        post = FeedbackPost(
            post_id="test_123",
            board_id="board_1",
            title="Test Post",
            content="Content",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        state: BugBridgeState = {
            "feedback_post": post,
            "bug_detection": None,
            "sentiment_analysis": None,
            "priority_score": None,
            "jira_ticket_id": "PROJ-123",
            "jira_ticket_url": "https://jira.example.com/browse/PROJ-123",
            "jira_ticket_status": "In Progress",
            "workflow_status": "ticket_created",
            "errors": [],
            "timestamps": {"collected_at": datetime.now(timezone.utc)},
            "metadata": {"source": "canny"},
        }
        
        assert state["feedback_post"] is not None
        assert state["jira_ticket_id"] == "PROJ-123"
        assert state["workflow_status"] == "ticket_created"
    
    def test_bug_bridge_state_all_workflow_statuses(self):
        """Test all valid workflow status values."""
        statuses = [
            "collected",
            "analyzed",
            "ticket_created",
            "monitoring",
            "resolved",
            "notified",
            "completed",
            "failed",
        ]
        
        for status in statuses:
            state: BugBridgeState = {
                "workflow_status": status,
                "errors": [],
                "timestamps": {},
                "metadata": {},
            }
            assert state["workflow_status"] == status


class TestModelSerialization:
    """Tests for model serialization to/from JSON."""
    
    def test_feedback_post_serialization(self):
        """Test FeedbackPost JSON serialization."""
        post = FeedbackPost(
            post_id="serial_test",
            board_id="board_1",
            title="Serialization Test",
            content="Test content",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Serialize to dict
        post_dict = post.model_dump()
        assert isinstance(post_dict, dict)
        assert post_dict["post_id"] == "serial_test"
        
        # Serialize to JSON string
        post_json = post.model_dump_json()
        assert isinstance(post_json, str)
        assert "serial_test" in post_json
    
    def test_bug_detection_result_serialization(self):
        """Test BugDetectionResult JSON serialization."""
        result = BugDetectionResult(
            is_bug=True,
            confidence=0.9,
            bug_severity="High",
            keywords_identified=["error", "bug"],
            reasoning="Test serialization of bug detection result",
        )
        
        result_dict = result.model_dump()
        assert result_dict["is_bug"] is True
        assert result_dict["confidence"] == 0.9
        assert isinstance(result_dict["keywords_identified"], list)
    
    def test_model_deserialization(self):
        """Test deserializing from dict."""
        data = {
            "post_id": "deserial_test",
            "board_id": "board_1",
            "title": "Deserialization Test",
            "content": "Test content",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        post = FeedbackPost.model_validate(data)
        assert post.post_id == "deserial_test"
        assert post.title == "Deserialization Test"

