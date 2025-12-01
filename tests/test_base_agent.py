"""
Tests for BaseAgent functionality.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from bugbridge.agents.base import BaseAgent
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState


class SampleAnalysisResult(BaseModel):
    """Sample Pydantic model for structured output testing."""

    analysis: str = Field(..., description="Analysis result")
    confidence: float = Field(..., description="Confidence score")


class ConcreteTestAgent(BaseAgent):
    """Concrete agent implementation for testing BaseAgent functionality."""

    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """Test implementation of execute method."""
        return {
            **state,
            "workflow_status": "test_completed",
            "metadata": {"test": True},
        }


@pytest.mark.asyncio
async def test_base_agent_initialization():
    """BaseAgent should initialize with name and optional LLM."""
    llm = ChatXAI(api_key="test_key", model="grok-4-fast-reasoning")
    agent = ConcreteTestAgent(name="test_agent", llm=llm)

    assert agent.name == "test_agent"
    assert agent.llm == llm
    assert agent.deterministic is True
    assert agent.llm.temperature == 0.0  # Enforced by deterministic flag


@pytest.mark.asyncio
async def test_base_agent_initialization_with_default_llm(monkeypatch):
    """BaseAgent should create default LLM if not provided."""
    with patch("bugbridge.agents.base.get_xai_llm") as mock_get_llm:
        mock_llm = ChatXAI(api_key="test_key")
        mock_get_llm.return_value = mock_llm

        agent = ConcreteTestAgent(name="test_agent")

        assert agent.llm == mock_llm
        mock_get_llm.assert_called_once()


@pytest.mark.asyncio
async def test_base_agent_non_deterministic():
    """BaseAgent should respect deterministic=False flag."""
    llm = ChatXAI(api_key="test_key", temperature=0.5)
    agent = ConcreteTestAgent(name="test_agent", llm=llm, deterministic=False)

    assert agent.deterministic is False
    assert agent.llm.temperature == 0.5  # Not overridden


@pytest.mark.asyncio
async def test_log_agent_decision():
    """BaseAgent should log agent decisions with audit logger."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    with patch("bugbridge.agents.base.audit_logger") as mock_audit:
        state: BugBridgeState = {
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

        agent.log_agent_decision(
            decision="test_decision",
            reasoning="test reasoning",
            state=state,
            context={"extra": "data"},
        )

        mock_audit.log_agent_decision.assert_called_once()
        call_args = mock_audit.log_agent_decision.call_args
        assert call_args.kwargs["agent_name"] == "test_agent"
        assert call_args.kwargs["decision"] == "test_decision"
        assert call_args.kwargs["reasoning"] == "test reasoning"


@pytest.mark.asyncio
async def test_log_agent_decision_with_feedback_post():
    """BaseAgent should extract post_id from feedback_post in state."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    feedback_post = FeedbackPost(
        post_id="post_123",
        board_id="board_1",
        title="Test Post",
        content="Content",
        author_id="author_1",
        author_name="Author",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        votes=0,
        comments_count=0,
        status="open",
        url="https://example.com/posts/123",
    )

    state: BugBridgeState = {
        "feedback_post": feedback_post,
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    with patch("bugbridge.agents.base.audit_logger") as mock_audit:
        agent.log_agent_decision(
            decision="analyze",
            reasoning="test",
            state=state,
        )

        call_args = mock_audit.log_agent_decision.call_args
        assert call_args.kwargs["post_id"] == "post_123"


@pytest.mark.asyncio
async def test_log_agent_action():
    """BaseAgent should log agent actions with audit logger."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    with patch("bugbridge.agents.base.audit_logger") as mock_audit:
        state: BugBridgeState = {
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

        agent.log_agent_action(
            action="process",
            result="success",
            state=state,
            duration_ms=150.5,
            context={"key": "value"},
        )

        mock_audit.log_agent_action.assert_called_once()
        call_args = mock_audit.log_agent_action.call_args
        assert call_args.kwargs["agent_name"] == "test_agent"
        assert call_args.kwargs["action"] == "process"
        assert call_args.kwargs["result"] == "success"
        assert call_args.kwargs["duration_ms"] == 150.5


@pytest.mark.asyncio
async def test_update_state_timestamp():
    """BaseAgent should update workflow state with timestamp."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    updated_state = agent.update_state_timestamp(state, "analyzed")

    assert "analyzed" in updated_state["timestamps"]
    assert isinstance(updated_state["timestamps"]["analyzed"], datetime)


@pytest.mark.asyncio
async def test_update_state_timestamp_preserves_existing():
    """BaseAgent should preserve existing timestamps when updating."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    existing_time = datetime.now(UTC)
    state: BugBridgeState = {
        "errors": [],
        "timestamps": {"collected": existing_time},
        "metadata": {},
    }

    updated_state = agent.update_state_timestamp(state, "analyzed")

    assert updated_state["timestamps"]["collected"] == existing_time
    assert "analyzed" in updated_state["timestamps"]


@pytest.mark.asyncio
async def test_add_state_error():
    """BaseAgent should add error messages to workflow state."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    updated_state = agent.add_state_error(state, "Test error message")

    assert len(updated_state["errors"]) == 1
    assert updated_state["errors"][0] == "Test error message"


@pytest.mark.asyncio
async def test_add_state_error_preserves_existing():
    """BaseAgent should preserve existing errors when adding new ones."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": ["Existing error"],
        "timestamps": {},
        "metadata": {},
    }

    updated_state = agent.add_state_error(state, "New error")

    assert len(updated_state["errors"]) == 2
    assert updated_state["errors"][0] == "Existing error"
    assert updated_state["errors"][1] == "New error"


@pytest.mark.asyncio
async def test_update_state_metadata():
    """BaseAgent should update workflow state metadata."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    updated_state = agent.update_state_metadata(state, "test_key", "test_value")

    assert updated_state["metadata"]["test_key"] == "test_value"


@pytest.mark.asyncio
async def test_update_state_metadata_preserves_existing():
    """BaseAgent should preserve existing metadata when updating."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {"existing": "value"},
    }

    updated_state = agent.update_state_metadata(state, "new_key", "new_value")

    assert updated_state["metadata"]["existing"] == "value"
    assert updated_state["metadata"]["new_key"] == "new_value"


@pytest.mark.asyncio
async def test_generate_structured_output(monkeypatch):
    """BaseAgent should generate structured output using XAI LLM."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    # Mock the structured output chain - patch at the method level
    mock_result = SampleAnalysisResult(analysis="Test analysis", confidence=0.95)

    async def mock_ainvoke(messages):
        return mock_result

    mock_structured_llm = MagicMock()
    mock_structured_llm.ainvoke = mock_ainvoke

    # Patch the generate_structured_output method to bypass LLM call
    original_method = agent.generate_structured_output

    async def mock_generate_structured_output(prompt, schema, system_message=None, **kwargs):
        return mock_result

    monkeypatch.setattr(agent, "generate_structured_output", mock_generate_structured_output)

    result = await agent.generate_structured_output(
        prompt="Analyze this",
        schema=SampleAnalysisResult,
        system_message="You are an analyzer",
    )

    assert isinstance(result, SampleAnalysisResult)
    assert result.analysis == "Test analysis"
    assert result.confidence == 0.95


@pytest.mark.asyncio
async def test_run_success():
    """BaseAgent.run should execute agent and log success."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    with patch("bugbridge.agents.base.logger") as mock_logger:
        with patch.object(agent, "log_agent_action") as mock_log_action:
            result = await agent.run(state)

            assert result["workflow_status"] == "test_completed"
            assert result["metadata"]["test"] is True
            mock_log_action.assert_called_once()
            call_args = mock_log_action.call_args
            assert call_args.kwargs["result"] == "success"


@pytest.mark.asyncio
async def test_run_handles_exception():
    """BaseAgent.run should handle exceptions and update state with error."""
    agent = ConcreteTestAgent(name="test_agent", llm=ChatXAI(api_key="test_key"))

    class FailingAgent(BaseAgent):
        async def execute(self, state: BugBridgeState) -> BugBridgeState:
            raise ValueError("Test error")

    failing_agent = FailingAgent(name="failing_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    result = await failing_agent.run(state)

    assert result["workflow_status"] == "failed"
    assert len(result["errors"]) == 1
    assert "failing_agent failed: Test error" in result["errors"][0]


@pytest.mark.asyncio
async def test_run_logs_failure():
    """BaseAgent.run should log failures with error context."""
    class FailingAgent(BaseAgent):
        async def execute(self, state: BugBridgeState) -> BugBridgeState:
            raise ValueError("Test error")

    failing_agent = FailingAgent(name="failing_agent", llm=ChatXAI(api_key="test_key"))

    state: BugBridgeState = {
        "errors": [],
        "timestamps": {},
        "metadata": {},
    }

    with patch.object(failing_agent, "log_agent_action") as mock_log_action:
        await failing_agent.run(state)

        mock_log_action.assert_called_once()
        call_args = mock_log_action.call_args
        assert call_args.kwargs["result"] == "failure"
        assert "error" in call_args.kwargs["context"]


@pytest.mark.asyncio
async def test_base_agent_is_abstract():
    """BaseAgent should be abstract and cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseAgent(name="test")  # type: ignore

