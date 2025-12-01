"""
Integration tests for the complete analysis pipeline.

Tests the full workflow: Feedback Collection → Bug Detection → 
Sentiment Analysis → Priority Scoring to ensure agents work together correctly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bugbridge.agents.bug_detection import BugDetectionAgent
from bugbridge.agents.collection import collect_feedback_node
from bugbridge.agents.priority import PriorityScoringAgent
from bugbridge.agents.sentiment import SentimentAnalysisAgent
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.workflows.main import execute_workflow


def make_feedback_post(post_id: str = "post_1") -> FeedbackPost:
    """Create a sample FeedbackPost."""
    return FeedbackPost(
        post_id=post_id,
        board_id="board_1",
        title="App crashes when clicking submit button",
        content="The application crashes immediately when I click the submit button. This is very frustrating and happens every time.",
        author_id="author_1",
        author_name="Test User",
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        votes=30,
        comments_count=12,
        status="open",
        url="https://example.canny.io/posts/post_1",
        tags=["bug", "urgent", "critical"],
    )


@pytest.mark.asyncio
async def test_analysis_pipeline_sequential_execution(monkeypatch):
    """Test the complete analysis pipeline executed sequentially."""
    # Mock feedback collection
    feedback_post = make_feedback_post("pipeline_test")

    # Create agents with mocked LLM
    bug_agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))
    sentiment_agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))
    priority_agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    # Mock bug detection result
    bug_result = BugDetectionResult(
        is_bug=True,
        confidence=0.95,
        bug_severity="Critical",
        keywords_identified=["crash", "error", "bug"],
        reasoning="The feedback describes a critical bug causing application crashes on button click.",
        analyzed_at=datetime.now(UTC),
    )

    async def mock_bug_generate(prompt, schema, system_message=None, **kwargs):
        return bug_result

    monkeypatch.setattr(bug_agent, "generate_structured_output", mock_bug_generate)

    # Mock sentiment analysis result
    sentiment_result = SentimentAnalysisResult(
        sentiment="Frustrated",
        sentiment_score=0.2,
        urgency="High",
        emotions_detected=["frustration", "anger", "disappointment"],
        reasoning="Strong negative sentiment with high urgency indicators.",
        analyzed_at=datetime.now(UTC),
    )

    async def mock_sentiment_generate(prompt, schema, system_message=None, **kwargs):
        return sentiment_result

    monkeypatch.setattr(sentiment_agent, "generate_structured_output", mock_sentiment_generate)

    # Mock priority scoring result
    priority_result = PriorityScoreResult(
        priority_score=90,
        is_burning_issue=True,
        recommended_jira_priority="Critical",
        priority_reasoning="Critical priority due to critical bug severity, high negative sentiment, and strong user engagement.",
        engagement_score=20.5,
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    async def mock_priority_generate(prompt, schema, system_message=None, **kwargs):
        return priority_result

    monkeypatch.setattr(priority_agent, "generate_structured_output", mock_priority_generate)

    # Initialize state with feedback post
    state: BugBridgeState = {
        "feedback_post": feedback_post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Execute bug detection
    state = await bug_agent.execute(state)
    assert state["bug_detection"] is not None
    assert state["bug_detection"].is_bug is True
    assert state["bug_detection"].bug_severity == "Critical"
    assert "bug_detected" in state["timestamps"]

    # Execute sentiment analysis
    state = await sentiment_agent.execute(state)
    assert state["sentiment_analysis"] is not None
    assert state["sentiment_analysis"].sentiment == "Frustrated"
    assert state["sentiment_analysis"].urgency == "High"
    assert "sentiment_analyzed" in state["timestamps"]

    # Execute priority scoring
    state = await priority_agent.execute(state)
    assert state["priority_score"] is not None
    assert state["priority_score"].priority_score == 90
    assert state["priority_score"].is_burning_issue is True
    assert state["priority_score"].recommended_jira_priority == "Critical"
    assert "priority_calculated" in state["timestamps"]

    # Verify final state
    assert state["feedback_post"] is not None
    assert state["bug_detection"] is not None
    assert state["sentiment_analysis"] is not None
    assert state["priority_score"] is not None
    assert state["workflow_status"] == "analyzed"


@pytest.mark.asyncio
async def test_workflow_pipeline_execution(monkeypatch):
    """Test the complete workflow execution through LangGraph nodes directly."""
    from bugbridge.agents.bug_detection import analyze_bug_node
    from bugbridge.agents.priority import calculate_priority_node
    from bugbridge.agents.sentiment import analyze_sentiment_node

    feedback_post = make_feedback_post("workflow_test")

    # Mock all agent LLM calls through the agent instances
    bug_result = BugDetectionResult(
        is_bug=True,
        confidence=0.92,
        bug_severity="High",
        keywords_identified=["crash", "error"],
        reasoning="Bug detected in workflow test.",
        analyzed_at=datetime.now(UTC),
    )

    sentiment_result = SentimentAnalysisResult(
        sentiment="Negative",
        sentiment_score=0.25,
        urgency="High",
        emotions_detected=["frustration"],
        reasoning="Negative sentiment detected.",
        analyzed_at=datetime.now(UTC),
    )

    priority_result = PriorityScoreResult(
        priority_score=75,
        is_burning_issue=True,
        recommended_jira_priority="High",
        priority_reasoning="High priority due to bug severity and sentiment.",
        engagement_score=18.0,
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    # Create agents and mock their structured output generation
    bug_agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))
    sentiment_agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))
    priority_agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    async def mock_bug_generate(prompt, schema, system_message=None, **kwargs):
        return bug_result

    async def mock_sentiment_generate(prompt, schema, system_message=None, **kwargs):
        return sentiment_result

    async def mock_priority_generate(prompt, schema, system_message=None, **kwargs):
        return priority_result

    monkeypatch.setattr(bug_agent, "generate_structured_output", mock_bug_generate)
    monkeypatch.setattr(sentiment_agent, "generate_structured_output", mock_sentiment_generate)
    monkeypatch.setattr(priority_agent, "generate_structured_output", mock_priority_generate)

    # Mock the agent getters to return our mocked agents
    with patch("bugbridge.agents.bug_detection.get_bug_detection_agent", return_value=bug_agent), \
         patch("bugbridge.agents.sentiment.get_sentiment_analysis_agent", return_value=sentiment_agent), \
         patch("bugbridge.agents.priority.get_priority_scoring_agent", return_value=priority_agent):

        # Start with feedback post (simulating collection step)
        state: BugBridgeState = {
            "feedback_post": feedback_post,
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

        # Execute through workflow nodes
        state = await analyze_bug_node(state)
        assert state["bug_detection"] is not None

        state = await analyze_sentiment_node(state)
        assert state["sentiment_analysis"] is not None

        state = await calculate_priority_node(state)
        assert state["priority_score"] is not None

        # Verify complete pipeline results
        assert state["feedback_post"] is not None
        assert state["bug_detection"] is not None
        assert state["sentiment_analysis"] is not None
        assert state["priority_score"] is not None
        assert state["priority_score"].priority_score == 75


@pytest.mark.asyncio
async def test_pipeline_state_propagation(monkeypatch):
    """Test that state is correctly propagated through the pipeline."""
    bug_agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))
    sentiment_agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))
    priority_agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    feedback_post = make_feedback_post("state_propagation_test")

    # Setup mocks
    bug_result = BugDetectionResult(
        is_bug=True,
        confidence=0.9,
        bug_severity="High",
        keywords_identified=["crash"],
        reasoning="Bug detected.",
        analyzed_at=datetime.now(UTC),
    )

    sentiment_result = SentimentAnalysisResult(
        sentiment="Negative",
        sentiment_score=0.3,
        urgency="Medium",
        emotions_detected=["frustration"],
        reasoning="Negative sentiment.",
        analyzed_at=datetime.now(UTC),
    )

    priority_result = PriorityScoreResult(
        priority_score=70,
        is_burning_issue=False,
        recommended_jira_priority="High",
        priority_reasoning="High priority score.",
        engagement_score=15.0,
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    async def mock_bug_generate(prompt, schema, system_message=None, **kwargs):
        return bug_result

    async def mock_sentiment_generate(prompt, schema, system_message=None, **kwargs):
        return sentiment_result

    async def mock_priority_generate(prompt, schema, system_message=None, **kwargs):
        return priority_result

    monkeypatch.setattr(bug_agent, "generate_structured_output", mock_bug_generate)
    monkeypatch.setattr(sentiment_agent, "generate_structured_output", mock_sentiment_generate)
    monkeypatch.setattr(priority_agent, "generate_structured_output", mock_priority_generate)

    # Start with feedback post
    state: BugBridgeState = {
        "feedback_post": feedback_post,
        "errors": [],
        "timestamps": {},
        "metadata": {"test": "state_propagation"},
    }

    # Verify initial state
    assert state["feedback_post"] is not None
    assert state.get("bug_detection") is None
    assert state.get("sentiment_analysis") is None
    assert state.get("priority_score") is None

    # Step 1: Bug detection
    state = await bug_agent.execute(state)
    assert state["bug_detection"] is not None
    assert state["feedback_post"] is not None  # Should be preserved
    assert state["metadata"]["test"] == "state_propagation"  # Should be preserved

    # Step 2: Sentiment analysis
    state = await sentiment_agent.execute(state)
    assert state["sentiment_analysis"] is not None
    assert state["bug_detection"] is not None  # Should be preserved
    assert state["feedback_post"] is not None  # Should be preserved

    # Step 3: Priority scoring
    state = await priority_agent.execute(state)
    assert state["priority_score"] is not None
    assert state["bug_detection"] is not None  # Should be preserved
    assert state["sentiment_analysis"] is not None  # Should be preserved
    assert state["feedback_post"] is not None  # Should be preserved


@pytest.mark.asyncio
async def test_pipeline_with_feature_request(monkeypatch):
    """Test pipeline with a feature request (not a bug)."""
    bug_agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))
    sentiment_agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))
    priority_agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    feature_post = make_feedback_post("feature_request")
    feature_post.title = "Feature Request: Dark Mode"
    feature_post.content = "I would love to see dark mode support in the app. This would be great for night-time usage."
    feature_post.tags = ["feature", "enhancement"]

    # Mock bug detection for feature request
    bug_result = BugDetectionResult(
        is_bug=False,
        confidence=0.88,
        bug_severity="N/A",
        keywords_identified=["feature", "request"],
        reasoning="This is a feature request, not a bug.",
        analyzed_at=datetime.now(UTC),
    )

    # Mock sentiment for positive feature request
    sentiment_result = SentimentAnalysisResult(
        sentiment="Positive",
        sentiment_score=0.75,
        urgency="Low",
        emotions_detected=["excitement", "hope"],
        reasoning="Positive sentiment for feature request.",
        analyzed_at=datetime.now(UTC),
    )

    # Mock priority for feature request (should be lower)
    priority_result = PriorityScoreResult(
        priority_score=35,
        is_burning_issue=False,
        recommended_jira_priority="Low",
        priority_reasoning="Lower priority for feature request with positive sentiment.",
        engagement_score=8.0,
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    async def mock_bug_generate(prompt, schema, system_message=None, **kwargs):
        return bug_result

    async def mock_sentiment_generate(prompt, schema, system_message=None, **kwargs):
        return sentiment_result

    async def mock_priority_generate(prompt, schema, system_message=None, **kwargs):
        return priority_result

    monkeypatch.setattr(bug_agent, "generate_structured_output", mock_bug_generate)
    monkeypatch.setattr(sentiment_agent, "generate_structured_output", mock_sentiment_generate)
    monkeypatch.setattr(priority_agent, "generate_structured_output", mock_priority_generate)

    state: BugBridgeState = {
        "feedback_post": feature_post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Execute pipeline
    state = await bug_agent.execute(state)
    assert state["bug_detection"].is_bug is False

    state = await sentiment_agent.execute(state)
    assert state["sentiment_analysis"].sentiment == "Positive"

    state = await priority_agent.execute(state)
    assert state["priority_score"].priority_score < 50  # Lower priority for feature
    assert state["priority_score"].is_burning_issue is False


@pytest.mark.asyncio
async def test_pipeline_error_handling(monkeypatch):
    """Test that errors in one agent don't break the entire pipeline."""
    bug_agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))
    sentiment_agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))
    priority_agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    feedback_post = make_feedback_post("error_test")

    # Bug detection succeeds
    bug_result = BugDetectionResult(
        is_bug=True,
        confidence=0.9,
        bug_severity="High",
        keywords_identified=["bug"],
        reasoning="Bug detected.",
        analyzed_at=datetime.now(UTC),
    )

    # Sentiment analysis fails
    async def mock_bug_generate(prompt, schema, system_message=None, **kwargs):
        return bug_result

    async def mock_sentiment_generate(prompt, schema, system_message=None, **kwargs):
        raise ValueError("Sentiment analysis API error")

    async def mock_priority_generate(prompt, schema, system_message=None, **kwargs):
        # Priority should still work even if sentiment fails
        return PriorityScoreResult(
            priority_score=60,
            is_burning_issue=False,
            recommended_jira_priority="Medium",
            priority_reasoning="Priority calculated without sentiment analysis.",
            engagement_score=12.0,
            sentiment_weight=0.3,
            bug_severity_weight=0.5,
            calculated_at=datetime.now(UTC),
        )

    monkeypatch.setattr(bug_agent, "generate_structured_output", mock_bug_generate)
    monkeypatch.setattr(sentiment_agent, "generate_structured_output", mock_sentiment_generate)
    monkeypatch.setattr(priority_agent, "generate_structured_output", mock_priority_generate)

    state: BugBridgeState = {
        "feedback_post": feedback_post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Bug detection should succeed
    state = await bug_agent.execute(state)
    assert state["bug_detection"] is not None

    # Sentiment analysis should fail gracefully
    state = await sentiment_agent.execute(state)
    assert len(state["errors"]) > 0
    assert state.get("sentiment_analysis") is None or "error" in str(state.get("sentiment_analysis", "")).lower()

    # Priority scoring should still work (can work without sentiment)
    state = await priority_agent.execute(state)
    assert state["priority_score"] is not None
    assert state["priority_score"].priority_score == 60


@pytest.mark.asyncio
async def test_pipeline_burning_issue_detection(monkeypatch):
    """Test pipeline correctly identifies burning issues."""
    bug_agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))
    sentiment_agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))
    priority_agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    critical_post = make_feedback_post("burning_issue")
    critical_post.votes = 100
    critical_post.comments_count = 50

    # Critical bug
    bug_result = BugDetectionResult(
        is_bug=True,
        confidence=0.98,
        bug_severity="Critical",
        keywords_identified=["crash", "data loss", "critical"],
        reasoning="Critical bug causing data loss.",
        analyzed_at=datetime.now(UTC),
    )

    # High urgency, frustrated sentiment
    sentiment_result = SentimentAnalysisResult(
        sentiment="Frustrated",
        sentiment_score=0.15,
        urgency="High",
        emotions_detected=["frustration", "anger", "panic"],
        reasoning="Extremely frustrated users with critical issue.",
        analyzed_at=datetime.now(UTC),
    )

    # High priority, burning issue
    priority_result = PriorityScoreResult(
        priority_score=95,
        is_burning_issue=True,
        recommended_jira_priority="Critical",
        priority_reasoning="Burning issue: Critical bug with high engagement and frustrated sentiment.",
        engagement_score=35.0,
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    async def mock_bug_generate(prompt, schema, system_message=None, **kwargs):
        return bug_result

    async def mock_sentiment_generate(prompt, schema, system_message=None, **kwargs):
        return sentiment_result

    async def mock_priority_generate(prompt, schema, system_message=None, **kwargs):
        return priority_result

    monkeypatch.setattr(bug_agent, "generate_structured_output", mock_bug_generate)
    monkeypatch.setattr(sentiment_agent, "generate_structured_output", mock_sentiment_generate)
    monkeypatch.setattr(priority_agent, "generate_structured_output", mock_priority_generate)

    state: BugBridgeState = {
        "feedback_post": critical_post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Execute pipeline
    state = await bug_agent.execute(state)
    state = await sentiment_agent.execute(state)
    state = await priority_agent.execute(state)

    # Verify burning issue is flagged
    assert state["priority_score"].is_burning_issue is True
    assert state["priority_score"].priority_score >= 90
    assert state["priority_score"].recommended_jira_priority == "Critical"
    assert state["bug_detection"].bug_severity == "Critical"
    assert state["sentiment_analysis"].urgency == "High"

