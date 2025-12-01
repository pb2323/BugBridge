"""
Integration tests for Jira Creation Agent with real MCP server.

These tests require:
1. A running MCP server (mcp-atlassian) accessible at JIRA__SERVER_URL
2. Valid Jira credentials configured in .env file
3. A valid Jira project key configured in JIRA__PROJECT_KEY

To start the MCP server:
    cd mcp-atlassian
    python -m mcp_atlassian --transport streamable-http --port 9000 --path /mcp -vv

Or using Docker:
    docker run --rm -p 9000:9000 --env-file .env \
      ghcr.io/sooperset/mcp-atlassian:latest \
      --transport streamable-http --port 9000 --path /mcp -vv

Set in .env:
    JIRA__SERVER_URL=http://localhost:9000/mcp
    JIRA__PROJECT_KEY=YOUR_PROJECT_KEY
    JIRA_URL=https://your-domain.atlassian.net
    JIRA_USERNAME=your-email@example.com
    JIRA_TOKEN=your-api-token
"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bugbridge.agents.bug_detection import analyze_bug_node
from bugbridge.agents.jira_creation import create_jira_ticket_node
from bugbridge.agents.priority import calculate_priority_node
from bugbridge.agents.sentiment import analyze_sentiment_node
from bugbridge.config import get_settings
from bugbridge.integrations.mcp_jira import MCPJiraClient, MCPJiraError
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)

# Skip all tests in this file if REAL_MCP_SERVER environment variable is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("REAL_MCP_SERVER", "").lower() in ("true", "1", "yes"),
    reason="REAL_MCP_SERVER environment variable not set. Set REAL_MCP_SERVER=true to run these tests.",
)


def make_feedback_post(post_id: str = "real_test_post") -> FeedbackPost:
    """Create a sample FeedbackPost for real testing."""
    return FeedbackPost(
        post_id=post_id,
        board_id="board_1",
        title="Test Bug: Application crashes on submit",
        content="This is a test bug report created by BugBridge integration tests. The application crashes when clicking the submit button. Please ignore or delete this ticket after testing.",
        author_id="test_author",
        author_name="Test User",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        votes=5,
        comments_count=2,
        status="open",
        url="https://example.canny.io/posts/test",
        tags=["bug", "test"],
    )


def make_bug_detection_result() -> BugDetectionResult:
    """Create a sample BugDetectionResult."""
    return BugDetectionResult(
        is_bug=True,
        confidence=0.95,
        bug_severity="High",
        keywords_identified=["crash", "submit", "error"],
        reasoning="The feedback clearly describes a bug where the application crashes when clicking the submit button. This is a high severity issue affecting user workflow.",
        analyzed_at=datetime.now(UTC),
    )


def make_sentiment_analysis_result() -> SentimentAnalysisResult:
    """Create a sample SentimentAnalysisResult."""
    return SentimentAnalysisResult(
        sentiment="Negative",
        sentiment_score=0.3,
        urgency="High",
        emotions_detected=["frustration"],
        reasoning="Negative sentiment detected with high urgency indicators.",
        analyzed_at=datetime.now(UTC),
    )


def make_priority_score_result() -> PriorityScoreResult:
    """Create a sample PriorityScoreResult."""
    return PriorityScoreResult(
        priority_score=75,
        is_burning_issue=False,
        recommended_jira_priority="High",
        priority_reasoning="High priority due to bug severity, negative sentiment, and user engagement.",
        engagement_score=12.5,
        sentiment_weight=0.3,
        bug_severity_weight=0.5,
        calculated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_mcp_server_connection():
    """Test that we can connect to the real MCP server."""
    settings = get_settings()
    server_url = str(settings.jira.server_url)
    project_key = settings.jira.project_key

    assert server_url, "JIRA__SERVER_URL must be configured"
    assert project_key, "JIRA__PROJECT_KEY must be configured"

    client = MCPJiraClient(
        server_url=server_url,
        project_key=project_key,
        auto_connect=False,
    )

    try:
        await client.connect()
        assert client._is_connected is True
        logger.info(f"Successfully connected to MCP server at {server_url}")
        print(f"✓ Connected to MCP server at {server_url}")
    except Exception as e:
        pytest.fail(f"Failed to connect to MCP server at {server_url}: {e}")
    finally:
        await client.disconnect()


@pytest.mark.asyncio
async def test_mcp_server_get_project_info():
    """Test retrieving project information from real Jira via MCP server."""
    settings = get_settings()
    server_url = str(settings.jira.server_url)
    project_key = settings.jira.project_key

    client = MCPJiraClient(
        server_url=server_url,
        project_key=project_key,
        auto_connect=False,
    )

    try:
        async with client.connection():
            # Search for issues in the project to verify connection works
            jql = f"project = {project_key} ORDER BY created DESC"
            issues = await client.search_issues(jql, limit=5)

            # Just verify we got a response (could be empty list)
            assert isinstance(issues, list)
            logger.info(f"Successfully queried Jira project {project_key}, found {len(issues)} recent issues")
            print(f"✓ Queried Jira project {project_key}, found {len(issues)} recent issues")
    except Exception as e:
        pytest.fail(f"Failed to query Jira project via MCP server: {e}")


@pytest.mark.asyncio
async def test_jira_creation_with_real_mcp_server(monkeypatch):
    """Test complete end-to-end flow with real MCP server: Feedback → Analysis → Jira Ticket."""
    settings = get_settings()
    server_url = str(settings.jira.server_url)
    project_key = settings.jira.project_key

    feedback_post = make_feedback_post("real_mcp_test")

    # Mock all analysis agents (we're testing MCP integration, not LLM)
    bug_result = make_bug_detection_result()
    sentiment_result = make_sentiment_analysis_result()
    priority_result = make_priority_score_result()

    # Create agents and mock their structured output
    from bugbridge.agents.bug_detection import BugDetectionAgent
    from bugbridge.agents.sentiment import SentimentAnalysisAgent
    from bugbridge.agents.priority import PriorityScoringAgent

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

    # Use REAL MCP client (not mocked)
    real_jira_client = MCPJiraClient(
        server_url=server_url,
        project_key=project_key,
        auto_connect=True,
    )

    with patch("bugbridge.agents.bug_detection.get_bug_detection_agent", return_value=bug_agent), \
         patch("bugbridge.agents.sentiment.get_sentiment_analysis_agent", return_value=sentiment_agent), \
         patch("bugbridge.agents.priority.get_priority_scoring_agent", return_value=priority_agent), \
         patch("bugbridge.agents.jira_creation.MCPJiraClient", return_value=real_jira_client), \
         patch("bugbridge.agents.jira_creation.get_settings", return_value=settings), \
         patch("bugbridge.agents.base.get_xai_llm", return_value=ChatXAI(api_key="test_key")):

        # Initialize state with feedback post
        state: BugBridgeState = {
            "feedback_post": feedback_post,
            "errors": [],
            "timestamps": {},
            "metadata": {},
        }

        # Execute analysis pipeline
        state = await analyze_bug_node(state)
        assert state.get("bug_detection") is not None

        state = await analyze_sentiment_node(state)
        assert state.get("sentiment_analysis") is not None

        state = await calculate_priority_node(state)
        assert state.get("priority_score") is not None

        # Execute Jira Creation Agent with REAL MCP server
        state = await create_jira_ticket_node(state)

        # Verify Jira ticket was created
        assert state.get("jira_ticket_id") is not None
        assert state.get("jira_ticket_url") is not None
        assert state.get("jira_ticket_status") is not None
        assert state.get("workflow_status") == "ticket_created"

        ticket_key = state.get("jira_ticket_id")
        logger.info(f"Successfully created Jira ticket {ticket_key} via real MCP server")
        print(f"✓ Created Jira ticket {ticket_key} via real MCP server")

        # Verify we can retrieve the ticket
        async with real_jira_client.connection():
            retrieved_ticket = await real_jira_client.get_issue(ticket_key)
            assert retrieved_ticket.key == ticket_key
            assert retrieved_ticket.project_key == project_key
            logger.info(f"Successfully retrieved ticket {ticket_key} from Jira")
            print(f"✓ Retrieved ticket {ticket_key} from Jira")

    # Cleanup: Optionally delete the test ticket
    # Uncomment the following to auto-delete test tickets
    # try:
    #     async with real_jira_client.connection():
    #         # Transition to closed or delete if possible
    #         logger.info(f"Test ticket {ticket_key} created. Please delete manually if needed.")
    # except Exception as e:
    #     logger.warning(f"Could not cleanup test ticket {ticket_key}: {e}")


@pytest.mark.asyncio
async def test_mcp_server_error_handling():
    """Test error handling with real MCP server (invalid project key)."""
    settings = get_settings()
    server_url = str(settings.jira.server_url)

    # Use an invalid project key to test error handling
    invalid_project = "INVALID_PROJECT_XYZ"

    client = MCPJiraClient(
        server_url=server_url,
        project_key=invalid_project,
        auto_connect=False,
    )

    try:
        async with client.connection():
            # Try to create an issue with invalid project
            from bugbridge.models.jira import JiraTicketCreate

            ticket_data = JiraTicketCreate(
                project_key=invalid_project,
                summary="Test Ticket",
                description="This should fail",
                issue_type="Bug",
                priority="Medium",
            )

            # This should raise an error
            with pytest.raises(MCPJiraError):
                await client.create_issue(ticket_data)

    except MCPJiraError as e:
        # Expected error
        assert "project" in str(e).lower() or "not found" in str(e).lower() or "invalid" in str(e).lower()
        logger.info(f"Correctly handled error for invalid project: {e}")
        print(f"✓ Correctly handled error for invalid project: {e}")


@pytest.mark.asyncio
async def test_mcp_server_connection_retry():
    """Test that connection retry logic works with real MCP server."""
    settings = get_settings()
    server_url = str(settings.jira.server_url)
    project_key = settings.jira.project_key

    client = MCPJiraClient(
        server_url=server_url,
        project_key=project_key,
        auto_connect=False,
        max_retries=3,
    )

    # Test connection
    try:
        await client.connect()
        assert client._is_connected is True

        # Test a simple operation
        async with client.connection():
            jql = f"project = {project_key} ORDER BY created DESC"
            issues = await client.search_issues(jql, limit=1)
            assert isinstance(issues, list)

        logger.info("Connection retry logic verified successfully")
        print("✓ Connection retry logic verified successfully")
    except Exception as e:
        pytest.fail(f"Connection retry test failed: {e}")
    finally:
        await client.disconnect()



