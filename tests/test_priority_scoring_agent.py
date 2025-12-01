"""
Tests for Priority Scoring Agent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bugbridge.agents.priority import (
    PriorityScoringAgent,
    calculate_engagement_score_from_post,
    calculate_priority_node,
    create_priority_scoring_prompt,
    is_burning_issue,
)
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState


def make_feedback_post(post_id: str = "post_1") -> FeedbackPost:
    """Create a sample FeedbackPost."""
    return FeedbackPost(
        post_id=post_id,
        board_id="board_1",
        title="Sample Post",
        content="The app crashes when I click the button",
        author_id="author_1",
        author_name="Author",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        votes=10,
        comments_count=3,
        status="open",
        url="https://example.canny.io/posts/post_1",
        tags=["urgent"],
    )


def make_bug_detection_result() -> BugDetectionResult:
    """Create a sample BugDetectionResult."""
    return BugDetectionResult(
        is_bug=True,
        confidence=0.92,
        bug_severity="High",
        keywords_identified=["crash", "error", "bug"],
        reasoning="The feedback describes a critical functionality issue.",
        analyzed_at=datetime.now(UTC),
    )


def make_sentiment_analysis_result() -> SentimentAnalysisResult:
    """Create a sample SentimentAnalysisResult."""
    return SentimentAnalysisResult(
        sentiment="Negative",
        sentiment_score=0.15,
        urgency="High",
        emotions_detected=["frustration", "anger"],
        reasoning="The feedback contains strong negative language indicating frustration.",
        analyzed_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_priority_scoring_agent_initialization():
    """PriorityScoringAgent should initialize correctly."""
    llm = ChatXAI(api_key="test_key", model="grok-4-fast-reasoning")
    agent = PriorityScoringAgent(llm=llm, sentiment_weight=0.3, bug_severity_weight=0.5)

    assert agent.name == "priority_scoring_agent"
    assert agent.llm == llm
    assert agent.deterministic is True
    assert agent.sentiment_weight == 0.3
    assert agent.bug_severity_weight == 0.5


def test_calculate_engagement_score_from_post():
    """calculate_engagement_score_from_post should calculate engagement score correctly."""
    post = make_feedback_post("engagement_test")
    post.votes = 10
    post.comments_count = 5

    score = calculate_engagement_score_from_post(post)

    assert score >= 0.0
    assert score > 0  # Should have some engagement with votes and comments


@pytest.mark.asyncio
async def test_is_burning_issue():
    """is_burning_issue should correctly identify burning issues."""
    bug_detection = make_bug_detection_result()
    sentiment = make_sentiment_analysis_result()

    # Critical bug + high urgency + high engagement = burning issue
    bug_detection.bug_severity = "Critical"
    sentiment.urgency = "High"

    result = is_burning_issue(bug_detection, sentiment, engagement_score=20.0)
    assert result is True

    # Low severity + low urgency + low engagement = not burning
    bug_detection.bug_severity = "Low"
    sentiment.urgency = "Low"

    result = is_burning_issue(bug_detection, sentiment, engagement_score=1.0)
    assert result is False


@pytest.mark.asyncio
async def test_create_priority_scoring_prompt():
    """create_priority_scoring_prompt should create formatted prompt."""
    post = make_feedback_post("test_post")
    bug_detection = make_bug_detection_result()
    sentiment = make_sentiment_analysis_result()

    prompt = create_priority_scoring_prompt(
        feedback_post=post,
        bug_detection=bug_detection,
        sentiment_analysis=sentiment,
        engagement_score=15.0,  # Actual engagement score range is 0-100, not 0-1
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
    )

    assert "Sample Post" in prompt
    assert "High" in prompt  # Bug severity
    assert "Negative" in prompt  # Sentiment
    assert "15.00" in prompt or "15" in prompt  # Engagement score
    assert "0.3" in prompt  # Sentiment weight
    assert "0.5" in prompt  # Bug severity weight


@pytest.mark.asyncio
async def test_priority_scoring_agent_execute_success(monkeypatch):
    """PriorityScoringAgent.execute should calculate priority and update state."""
    agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    # Mock structured output generation
    mock_result = PriorityScoreResult(
        priority_score=75,
        is_burning_issue=True,
        recommended_jira_priority="High",
        priority_reasoning="High priority due to critical bug severity and negative sentiment with high engagement.",
        engagement_score=15.0,  # Actual engagement score range is 0-100
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    # Mock the generate_structured_output method
    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    state: BugBridgeState = {
        "feedback_post": make_feedback_post("test_post"),
        "bug_detection": make_bug_detection_result(),
        "sentiment_analysis": make_sentiment_analysis_result(),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["priority_score"] is not None
    assert result_state["priority_score"].priority_score == 75
    assert result_state["priority_score"].is_burning_issue is True
    assert result_state["priority_score"].recommended_jira_priority == "High"
    # Engagement score is calculated from the post, not from the mock result
    assert result_state["priority_score"].engagement_score >= 0.0
    assert result_state["workflow_status"] == "analyzed"
    assert "priority_calculated" in result_state["timestamps"]


@pytest.mark.asyncio
async def test_priority_scoring_agent_execute_no_feedback_post():
    """PriorityScoringAgent.execute should handle missing feedback_post."""
    agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert len(result_state["errors"]) == 1
    assert "requires feedback_post" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_priority_scoring_agent_execute_missing_analysis(monkeypatch):
    """PriorityScoringAgent.execute should work with missing bug/sentiment analysis."""
    agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    # Mock structured output generation
    mock_result = PriorityScoreResult(
        priority_score=50,
        is_burning_issue=False,
        recommended_jira_priority="Medium",
        priority_reasoning="Medium priority with limited analysis data available.",
        engagement_score=5.0,  # Actual engagement score range
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    # State with only feedback_post, no analysis results
    state: BugBridgeState = {
        "feedback_post": make_feedback_post("test_post"),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["priority_score"] is not None
    assert result_state["priority_score"].priority_score == 50


@pytest.mark.asyncio
async def test_priority_scoring_agent_execute_error_handling(monkeypatch):
    """PriorityScoringAgent.execute should handle LLM errors gracefully."""
    agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    # Mock structured output to raise error
    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        raise ValueError("LLM API error")

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    state: BugBridgeState = {
        "feedback_post": make_feedback_post("error_post"),
        "bug_detection": make_bug_detection_result(),
        "sentiment_analysis": make_sentiment_analysis_result(),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert len(result_state["errors"]) == 1
    assert "Priority scoring failed" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_priority_scoring_agent_with_dict_inputs(monkeypatch):
    """PriorityScoringAgent.execute should handle dict inputs for bug/sentiment analysis."""
    agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    mock_result = PriorityScoreResult(
        priority_score=70,
        is_burning_issue=False,
        recommended_jira_priority="High",
        priority_reasoning="Test priority scoring result.",
        engagement_score=10.0,  # Actual engagement score range
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    # Use dicts instead of objects
    bug_dict = make_bug_detection_result().model_dump()
    sentiment_dict = make_sentiment_analysis_result().model_dump()

    state: BugBridgeState = {
        "feedback_post": make_feedback_post("dict_test"),
        "bug_detection": bug_dict,
        "sentiment_analysis": sentiment_dict,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["priority_score"] is not None
    assert result_state["priority_score"].priority_score == 70


@pytest.mark.asyncio
async def test_priority_scoring_agent_low_priority(monkeypatch):
    """PriorityScoringAgent.execute should handle low priority cases."""
    agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    # Mock structured output for low priority
    mock_result = PriorityScoreResult(
        priority_score=25,
        is_burning_issue=False,
        recommended_jira_priority="Low",
        priority_reasoning="Low priority due to minor issue with low engagement and neutral sentiment.",
        engagement_score=2.0,  # Actual engagement score range
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    bug_detection = make_bug_detection_result()
    bug_detection.bug_severity = "Low"
    bug_detection.is_bug = False

    sentiment = make_sentiment_analysis_result()
    sentiment.urgency = "Low"
    sentiment.sentiment = "Neutral"
    sentiment.sentiment_score = 0.5

    post = make_feedback_post("low_priority")
    post.votes = 1
    post.comments_count = 0

    state: BugBridgeState = {
        "feedback_post": post,
        "bug_detection": bug_detection,
        "sentiment_analysis": sentiment,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["priority_score"].priority_score == 25
    assert result_state["priority_score"].is_burning_issue is False
    assert result_state["priority_score"].recommended_jira_priority == "Low"


@pytest.mark.asyncio
async def test_calculate_priority_node(monkeypatch):
    """calculate_priority_node should execute agent and return updated state."""
    # Mock the agent's run method
    mock_result_state: BugBridgeState = {
        "feedback_post": make_feedback_post("node_test"),
        "bug_detection": make_bug_detection_result(),
        "sentiment_analysis": make_sentiment_analysis_result(),
        "priority_score": PriorityScoreResult(
            priority_score=75,
            is_burning_issue=True,
            recommended_jira_priority="High",
            priority_reasoning="Test priority scoring result.",
            engagement_score=15.0,  # Actual engagement score range is 0-100
            sentiment_weight=0.3,
            bug_severity_weight=0.5,
            calculated_at=datetime.now(UTC),
        ),
        "workflow_status": "analyzed",
        "errors": [],
        "timestamps": {"priority_calculated": datetime.now(UTC)},
        "metadata": {},
    }

    async def mock_run(state):
        return mock_result_state

    with patch("bugbridge.agents.priority.get_priority_scoring_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=mock_run)
        mock_get_agent.return_value = mock_agent

        state: BugBridgeState = {
            "feedback_post": make_feedback_post("node_test"),
            "bug_detection": make_bug_detection_result(),
            "sentiment_analysis": make_sentiment_analysis_result(),
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

        result = await calculate_priority_node(state)

        assert result["priority_score"] is not None
        assert result["workflow_status"] == "analyzed"

