"""
Tests for Sentiment Analysis Agent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bugbridge.agents.sentiment import (
    SentimentAnalysisAgent,
    analyze_sentiment_node,
    create_sentiment_analysis_prompt,
)
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.analysis import SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState


def make_feedback_post(post_id: str = "post_1") -> FeedbackPost:
    """Create a sample FeedbackPost."""
    return FeedbackPost(
        post_id=post_id,
        board_id="board_1",
        title="Sample Post",
        content="This feature is really frustrating and needs to be fixed immediately!",
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


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_initialization():
    """SentimentAnalysisAgent should initialize correctly."""
    llm = ChatXAI(api_key="test_key", model="grok-4-fast-reasoning")
    agent = SentimentAnalysisAgent(llm=llm)

    assert agent.name == "sentiment_analysis_agent"
    assert agent.llm == llm
    assert agent.deterministic is True


@pytest.mark.asyncio
async def test_create_sentiment_analysis_prompt():
    """create_sentiment_analysis_prompt should create formatted prompt."""
    post = make_feedback_post("test_post")

    prompt = create_sentiment_analysis_prompt(post)

    assert "Sample Post" in prompt
    assert "This feature is really frustrating" in prompt
    assert "Votes: 10" in prompt
    assert "Comments: 3" in prompt
    assert "Tags: urgent" in prompt


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_execute_success(monkeypatch):
    """SentimentAnalysisAgent.execute should analyze sentiment and update state."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))

    # Mock structured output generation
    mock_result = SentimentAnalysisResult(
        sentiment="Negative",
        sentiment_score=0.15,  # Low score = negative sentiment (1.0 - 0.85 = 0.15)
        urgency="High",
        emotions_detected=["frustration", "anger", "disappointment"],
        reasoning="The feedback contains strong negative language indicating frustration and urgency.",
        analyzed_at=datetime.now(UTC),
    )

    # Mock the generate_structured_output method
    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    state: BugBridgeState = {
        "feedback_post": make_feedback_post("test_post"),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["sentiment_analysis"] is not None
    assert result_state["sentiment_analysis"].sentiment == "Negative"
    assert result_state["sentiment_analysis"].sentiment_score == 0.15
    assert result_state["sentiment_analysis"].urgency == "High"
    assert result_state["workflow_status"] == "analyzed"
    assert "sentiment_analyzed" in result_state["timestamps"]


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_execute_positive_sentiment(monkeypatch):
    """SentimentAnalysisAgent.execute should handle positive sentiment correctly."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))

    # Mock structured output for positive sentiment
    mock_result = SentimentAnalysisResult(
        sentiment="Positive",
        sentiment_score=0.75,
        urgency="Low",
        emotions_detected=["happiness", "satisfaction", "excitement"],
        reasoning="The feedback expresses positive sentiment and appreciation for the feature.",
        analyzed_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    post = make_feedback_post("positive_post")
    post.content = "Love this new feature! It's exactly what I needed. Thank you!"
    post.title = "Great feature!"

    state: BugBridgeState = {
        "feedback_post": post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["sentiment_analysis"].sentiment == "Positive"
    assert result_state["sentiment_analysis"].sentiment_score == 0.75
    assert result_state["sentiment_analysis"].urgency == "Low"


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_execute_neutral_sentiment(monkeypatch):
    """SentimentAnalysisAgent.execute should handle neutral sentiment correctly."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))

    # Mock structured output for neutral sentiment
    mock_result = SentimentAnalysisResult(
        sentiment="Neutral",
        sentiment_score=0.5,  # Middle score for neutral
        urgency="Medium",
        emotions_detected=["neutral", "curiosity"],
        reasoning="The feedback is neutral, presenting factual information without strong emotion.",
        analyzed_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    post = make_feedback_post("neutral_post")
    post.content = "I noticed the feature could be improved by adding an option to customize the settings."

    state: BugBridgeState = {
        "feedback_post": post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["sentiment_analysis"].sentiment == "Neutral"
    assert result_state["sentiment_analysis"].sentiment_score == 0.5
    assert result_state["sentiment_analysis"].urgency == "Medium"


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_execute_no_feedback_post():
    """SentimentAnalysisAgent.execute should handle missing feedback_post."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert len(result_state["errors"]) == 1
    assert "requires feedback_post" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_execute_error_handling(monkeypatch):
    """SentimentAnalysisAgent.execute should handle LLM errors gracefully."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))

    # Mock structured output to raise error
    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        raise ValueError("LLM API error")

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    state: BugBridgeState = {
        "feedback_post": make_feedback_post("error_post"),
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert len(result_state["errors"]) == 1
    assert "Sentiment analysis failed" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_sentiment_analysis_agent_with_dict_feedback_post(monkeypatch):
    """SentimentAnalysisAgent.execute should handle dict feedback_post."""
    agent = SentimentAnalysisAgent(llm=ChatXAI(api_key="test_key"))

    mock_result = SentimentAnalysisResult(
        sentiment="Negative",
        sentiment_score=0.2,  # Low score = negative sentiment
        urgency="High",
        emotions_detected=["frustration"],
        reasoning="Test sentiment analysis result.",
        analyzed_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    # Use dict instead of FeedbackPost object
    post_dict = make_feedback_post("dict_post").model_dump()

    state: BugBridgeState = {
        "feedback_post": post_dict,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["sentiment_analysis"] is not None
    assert result_state["sentiment_analysis"].sentiment == "Negative"


@pytest.mark.asyncio
async def test_analyze_sentiment_node(monkeypatch):
    """analyze_sentiment_node should execute agent and return updated state."""
    # Mock the agent's run method
    mock_result_state: BugBridgeState = {
        "feedback_post": make_feedback_post("node_test"),
        "sentiment_analysis": SentimentAnalysisResult(
            sentiment="Negative",
            sentiment_score=0.2,
            urgency="High",
            emotions_detected=["frustration"],
            reasoning="Test analysis result.",
            analyzed_at=datetime.now(UTC),
        ),
        "workflow_status": "analyzed",
        "errors": [],
        "timestamps": {"sentiment_analyzed": datetime.now(UTC)},
        "metadata": {},
    }

    async def mock_run(state):
        return mock_result_state

    with patch("bugbridge.agents.sentiment.get_sentiment_analysis_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=mock_run)
        mock_get_agent.return_value = mock_agent

        state: BugBridgeState = {
            "feedback_post": make_feedback_post("node_test"),
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

        result = await analyze_sentiment_node(state)

        assert result["sentiment_analysis"] is not None
        assert result["workflow_status"] == "analyzed"

