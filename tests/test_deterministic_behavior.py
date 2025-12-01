"""
Tests for deterministic behavior of analysis agents.

Ensures that the same input produces the same output across multiple runs,
which is critical for reproducible analysis and debugging.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from bugbridge.agents.bug_detection import BugDetectionAgent
from bugbridge.agents.priority import PriorityScoringAgent
from bugbridge.agents.sentiment import SentimentAnalysisAgent
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState


def make_feedback_post(post_id: str = "post_1") -> FeedbackPost:
    """Create a sample FeedbackPost."""
    return FeedbackPost(
        post_id=post_id,
        board_id="board_1",
        title="The app crashes when I click the button",
        content="Whenever I try to click the submit button, the app crashes immediately. This is very frustrating.",
        author_id="author_1",
        author_name="Test User",
        created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        updated_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        votes=25,
        comments_count=8,
        status="open",
        url="https://example.canny.io/posts/post_1",
        tags=["bug", "urgent"],
    )


def make_bug_detection_result() -> BugDetectionResult:
    """Create a consistent BugDetectionResult."""
    return BugDetectionResult(
        is_bug=True,
        confidence=0.92,
        bug_severity="High",
        keywords_identified=["crash", "error", "bug"],
        reasoning="The feedback describes a critical functionality issue where the app crashes on button click.",
        analyzed_at=datetime(2024, 1, 15, 10, 5, 0, tzinfo=UTC),
    )


def make_sentiment_analysis_result() -> SentimentAnalysisResult:
    """Create a consistent SentimentAnalysisResult."""
    return SentimentAnalysisResult(
        sentiment="Frustrated",
        sentiment_score=0.2,
        urgency="High",
        emotions_detected=["frustration", "concern"],
        reasoning="The feedback contains strong negative language indicating frustration and urgency.",
        analyzed_at=datetime(2024, 1, 15, 10, 6, 0, tzinfo=UTC),
    )


def make_priority_score_result() -> PriorityScoreResult:
    """Create a consistent PriorityScoreResult."""
    return PriorityScoreResult(
        priority_score=82,
        is_burning_issue=True,
        recommended_jira_priority="High",
        priority_reasoning="High priority due to critical bug severity, high negative sentiment, and strong user engagement.",
        engagement_score=18.5,
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime(2024, 1, 15, 10, 7, 0, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_bug_detection_agent_temperature_setting():
    """BugDetectionAgent should have temperature=0 for deterministic behavior."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key", model="grok-4-fast-reasoning"))

    assert agent.deterministic is True
    assert agent.llm.temperature == 0.0


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_temperature_setting():
    """SentimentAnalysisAgent should have temperature=0 for deterministic behavior."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key", model="grok-4-fast-reasoning"))

    assert agent.deterministic is True
    assert agent.llm.temperature == 0.0


@pytest.mark.asyncio
async def test_priority_scoring_agent_temperature_setting():
    """PriorityScoringAgent should have temperature=0 for deterministic behavior."""
    agent = PriorityScoringAgent(llm=ChatXAI(api_key="test_key", model="grok-4-fast-reasoning"))

    assert agent.deterministic is True
    assert agent.llm.temperature == 0.0


@pytest.mark.asyncio
async def test_bug_detection_deterministic_output(monkeypatch):
    """BugDetectionAgent should produce identical outputs for identical inputs."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    # Create a consistent mock result
    mock_result = make_bug_detection_result()

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    # Create identical input state
    input_state: BugBridgeState = {
        "feedback_post": make_feedback_post("deterministic_test"),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Run multiple times
    results = []
    for _ in range(3):
        result_state = await agent.execute(input_state.copy())
        results.append(result_state)

    # Verify all results are identical (excluding timestamps which may vary)
    assert len(results) == 3

    # Check that bug detection results are identical
    for i in range(1, len(results)):
        result1 = results[0]["bug_detection"]
        result2 = results[i]["bug_detection"]

        assert result1.is_bug == result2.is_bug
        assert result1.confidence == result2.confidence
        assert result1.bug_severity == result2.bug_severity
        assert result1.keywords_identified == result2.keywords_identified
        assert result1.reasoning == result2.reasoning


@pytest.mark.asyncio
async def test_sentiment_analysis_deterministic_output(monkeypatch):
    """SentimentAnalysisAgent should produce identical outputs for identical inputs."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))

    # Create a consistent mock result
    mock_result = make_sentiment_analysis_result()

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    # Create identical input state
    input_state: BugBridgeState = {
        "feedback_post": make_feedback_post("deterministic_test"),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Run multiple times
    results = []
    for _ in range(3):
        result_state = await agent.execute(input_state.copy())
        results.append(result_state)

    # Verify all results are identical
    assert len(results) == 3

    # Check that sentiment analysis results are identical
    for i in range(1, len(results)):
        result1 = results[0]["sentiment_analysis"]
        result2 = results[i]["sentiment_analysis"]

        assert result1.sentiment == result2.sentiment
        assert result1.sentiment_score == result2.sentiment_score
        assert result1.urgency == result2.urgency
        assert result1.emotions_detected == result2.emotions_detected
        assert result1.reasoning == result2.reasoning


@pytest.mark.asyncio
async def test_priority_scoring_deterministic_output(monkeypatch):
    """PriorityScoringAgent should produce identical outputs for identical inputs."""
    agent = PriorityScoringAgent(
        llm=ChatXAI(api_key="test_key"), sentiment_weight=0.3, bug_severity_weight=0.5
    )

    # Create a consistent mock result
    mock_result = make_priority_score_result()

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    # Create identical input state
    input_state: BugBridgeState = {
        "feedback_post": make_feedback_post("deterministic_test"),
        "bug_detection": make_bug_detection_result(),
        "sentiment_analysis": make_sentiment_analysis_result(),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Run multiple times
    results = []
    for _ in range(3):
        result_state = await agent.execute(input_state.copy())
        results.append(result_state)

    # Verify all results are identical
    assert len(results) == 3

    # Check that priority score results are identical
    for i in range(1, len(results)):
        result1 = results[0]["priority_score"]
        result2 = results[i]["priority_score"]

        assert result1.priority_score == result2.priority_score
        assert result1.is_burning_issue == result2.is_burning_issue
        assert result1.recommended_jira_priority == result2.recommended_jira_priority
        assert result1.priority_reasoning == result2.priority_reasoning
        assert result1.engagement_score == result2.engagement_score


@pytest.mark.asyncio
async def test_deterministic_structured_output_validation(monkeypatch):
    """Structured outputs should be consistently validated across runs."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    # Mock result that will be validated
    mock_result = make_bug_detection_result()

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        # Verify that schema is always the same
        assert schema == BugDetectionResult
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    input_state: BugBridgeState = {
        "feedback_post": make_feedback_post("validation_test"),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Run multiple times - validation should be consistent
    for _ in range(3):
        result_state = await agent.execute(input_state.copy())
        # Verify result is a valid BugDetectionResult
        assert isinstance(result_state["bug_detection"], BugDetectionResult)
        assert result_state["bug_detection"].is_bug is True
        assert 0.0 <= result_state["bug_detection"].confidence <= 1.0


@pytest.mark.asyncio
async def test_deterministic_prompt_generation():
    """Prompts should be identical for identical inputs."""
    from bugbridge.agents.bug_detection import create_bug_detection_prompt
    from bugbridge.agents.priority import create_priority_scoring_prompt
    from bugbridge.agents.sentiment import create_sentiment_analysis_prompt

    post = make_feedback_post("prompt_test")

    # Generate prompts multiple times
    bug_prompts = [create_bug_detection_prompt(post) for _ in range(3)]
    sentiment_prompts = [create_sentiment_analysis_prompt(post) for _ in range(3)]

    bug_detection = make_bug_detection_result()
    sentiment = make_sentiment_analysis_result()
    priority_prompts = [
        create_priority_scoring_prompt(
            feedback_post=post,
            bug_detection=bug_detection,
            sentiment_analysis=sentiment,
            engagement_score=18.5,
            sentiment_weight=0.3,
            bug_severity_weight=0.5,
        )
        for _ in range(3)
    ]

    # All prompts should be identical
    assert len(set(bug_prompts)) == 1, "Bug detection prompts should be identical"
    assert len(set(sentiment_prompts)) == 1, "Sentiment analysis prompts should be identical"
    assert len(set(priority_prompts)) == 1, "Priority scoring prompts should be identical"


@pytest.mark.asyncio
async def test_deterministic_state_updates(monkeypatch):
    """State updates should be deterministic and consistent."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    mock_result = make_bug_detection_result()

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    input_state: BugBridgeState = {
        "feedback_post": make_feedback_post("state_test"),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    # Run multiple times
    results = []
    for _ in range(3):
        result_state = await agent.execute(input_state.copy())
        results.append(result_state)

    # Verify workflow_status is consistently set
    for result in results:
        assert result["workflow_status"] == "analyzed"

    # Verify all results have bug_detection
    for result in results:
        assert "bug_detection" in result
        assert result["bug_detection"] is not None

    # Verify timestamps are set (may vary in value but should all be set)
    for result in results:
        assert "bug_detected" in result["timestamps"]
        assert result["timestamps"]["bug_detected"] is not None


@pytest.mark.asyncio
async def test_deterministic_with_different_inputs(monkeypatch):
    """Agents should produce different but consistent outputs for different inputs."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    # Mock different results for different inputs
    bug_post = make_feedback_post("bug_post")
    bug_post.title = "App crashes on button click"
    bug_post.content = "The app crashes when I click the button"

    feature_post = make_feedback_post("feature_post")
    feature_post.title = "Feature request: Dark mode"
    feature_post.content = "I would love to see dark mode support in the app"

    # Track which post was analyzed
    analyzed_posts = []

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        # Return different results based on content - check for feature request keywords
        if "dark mode" in prompt.lower() or "would love" in prompt.lower():
            analyzed_posts.append("feature")
            return BugDetectionResult(
                is_bug=False,
                confidence=0.85,
                bug_severity="N/A",
                keywords_identified=["feature", "request"],
                reasoning="Feature request detected in prompt content.",
                analyzed_at=datetime.now(UTC),
            )
        else:
            analyzed_posts.append("bug")
            return BugDetectionResult(
                is_bug=True,
                confidence=0.92,
                bug_severity="High",
                keywords_identified=["crash", "error"],
                reasoning="Bug detected in prompt content.",
                analyzed_at=datetime.now(UTC),
            )

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    # Test with bug post
    bug_state: BugBridgeState = {
        "feedback_post": bug_post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }
    bug_result = await agent.execute(bug_state)

    # Test with feature post
    feature_state: BugBridgeState = {
        "feedback_post": feature_post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }
    feature_result = await agent.execute(feature_state)

    # Results should be different but each should be consistent
    assert bug_result["bug_detection"].is_bug is True
    assert feature_result["bug_detection"].is_bug is False

    # Running again should produce same results
    bug_result2 = await agent.execute(bug_state)
    feature_result2 = await agent.execute(feature_state)

    assert bug_result["bug_detection"].is_bug == bug_result2["bug_detection"].is_bug
    assert feature_result["bug_detection"].is_bug == feature_result2["bug_detection"].is_bug

