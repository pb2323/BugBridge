"""
Tests for Bug Detection Agent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bugbridge.agents.bug_detection import BugDetectionAgent, analyze_bug_node, create_bug_detection_prompt
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.analysis import BugDetectionResult
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
        votes=5,
        comments_count=1,
        status="open",
        url="https://example.canny.io/posts/post_1",
        tags=["bug"],
    )


@pytest.mark.asyncio
async def test_bug_detection_agent_initialization():
    """BugDetectionAgent should initialize correctly."""
    llm = ChatXAI(api_key="test_key", model="grok-4-fast-reasoning")
    agent = BugDetectionAgent(llm=llm)

    assert agent.name == "bug_detection_agent"
    assert agent.llm == llm
    assert agent.deterministic is True


@pytest.mark.asyncio
async def test_create_bug_detection_prompt():
    """create_bug_detection_prompt should create formatted prompt."""
    post = make_feedback_post("test_post")

    prompt = create_bug_detection_prompt(post)

    assert "Sample Post" in prompt
    assert "The app crashes when I click the button" in prompt
    assert "Votes: 5" in prompt
    assert "Comments: 1" in prompt
    assert "Tags: bug" in prompt


@pytest.mark.asyncio
async def test_bug_detection_agent_execute_success(monkeypatch):
    """BugDetectionAgent.execute should analyze feedback and update state."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    # Mock structured output generation
    mock_result = BugDetectionResult(
        is_bug=True,
        confidence=0.92,
        bug_severity="High",
        keywords_identified=["crash", "button", "error"],
        reasoning="The feedback describes a crash when clicking a button, which indicates a critical functionality issue.",
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

    assert result_state["bug_detection"] is not None
    assert result_state["bug_detection"].is_bug is True
    assert result_state["bug_detection"].confidence == 0.92
    assert result_state["bug_detection"].bug_severity == "High"
    assert result_state["workflow_status"] == "analyzed"
    assert "bug_detected" in result_state["timestamps"]


@pytest.mark.asyncio
async def test_bug_detection_agent_execute_no_feedback_post():
    """BugDetectionAgent.execute should handle missing feedback_post."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert len(result_state["errors"]) == 1
    assert "requires feedback_post" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_bug_detection_agent_execute_feature_request(monkeypatch):
    """BugDetectionAgent.execute should correctly identify feature requests."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    # Mock structured output for feature request
    mock_result = BugDetectionResult(
        is_bug=False,
        confidence=0.85,
        bug_severity="N/A",
        keywords_identified=["feature", "request", "enhancement"],
        reasoning="The feedback describes a new feature request rather than a bug report.",
        analyzed_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    post = make_feedback_post("feature_post")
    post.content = "I would love to see dark mode support in the app"
    post.title = "Feature request: Dark mode"

    state: BugBridgeState = {
        "feedback_post": post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["bug_detection"].is_bug is False
    assert result_state["bug_detection"].bug_severity == "N/A"
    assert result_state["bug_detection"].confidence == 0.85


@pytest.mark.asyncio
async def test_bug_detection_agent_execute_critical_bug(monkeypatch):
    """BugDetectionAgent.execute should handle critical bugs correctly."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    # Mock structured output for critical bug
    mock_result = BugDetectionResult(
        is_bug=True,
        confidence=0.98,
        bug_severity="Critical",
        keywords_identified=["crash", "data loss", "critical", "error"],
        reasoning="The feedback describes a critical bug causing data loss and system crashes.",
        analyzed_at=datetime.now(UTC),
    )

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    post = make_feedback_post("critical_bug")
    post.content = "The app crashes and loses all user data when saving"

    state: BugBridgeState = {
        "feedback_post": post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result_state = await agent.execute(state)

    assert result_state["bug_detection"].is_bug is True
    assert result_state["bug_detection"].bug_severity == "Critical"
    assert result_state["bug_detection"].confidence == 0.98


@pytest.mark.asyncio
async def test_bug_detection_agent_execute_error_handling(monkeypatch):
    """BugDetectionAgent.execute should handle LLM errors gracefully."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

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
    assert "Bug detection analysis failed" in result_state["errors"][0]


@pytest.mark.asyncio
async def test_bug_detection_agent_with_dict_feedback_post(monkeypatch):
    """BugDetectionAgent.execute should handle dict feedback_post."""
    agent = BugDetectionAgent(llm=ChatXAI(api_key="test_key"))

    mock_result = BugDetectionResult(
        is_bug=True,
        confidence=0.9,
        bug_severity="High",
        keywords_identified=["bug"],
        reasoning="Test bug detection result.",
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

    assert result_state["bug_detection"] is not None
    assert result_state["bug_detection"].is_bug is True


@pytest.mark.asyncio
async def test_analyze_bug_node(monkeypatch):
    """analyze_bug_node should execute agent and return updated state."""
    # Mock the agent's run method
    mock_result_state: BugBridgeState = {
        "feedback_post": make_feedback_post("node_test"),
        "bug_detection": BugDetectionResult(
            is_bug=True,
            confidence=0.9,
            bug_severity="High",
            keywords_identified=["bug"],
            reasoning="Test analysis result.",
            analyzed_at=datetime.now(UTC),
        ),
        "workflow_status": "analyzed",
        "errors": [],
        "timestamps": {"bug_detected": datetime.now(UTC)},
        "metadata": {},
    }

    async def mock_run(state):
        return mock_result_state

    with patch("bugbridge.agents.bug_detection.get_bug_detection_agent") as mock_get_agent:
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=mock_run)
        mock_get_agent.return_value = mock_agent

        state: BugBridgeState = {
            "feedback_post": make_feedback_post("node_test"),
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

        result = await analyze_bug_node(state)

        assert result["bug_detection"] is not None
        assert result["workflow_status"] == "analyzed"

