"""
Unit Tests for Reporting Agent

Tests the Reporting Agent with mocked database queries and LLM responses.
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from bugbridge.agents.reporting import (
    ReportingAgent,
    DailyMetrics,
    ReportSummary,
    query_daily_metrics,
    create_report_prompt,
    format_report_markdown,
    get_reporting_agent,
)
from bugbridge.database.models import (
    FeedbackPost as DBFeedbackPost,
    AnalysisResult,
    JiraTicket as DBJiraTicket,
    Report,
)
from bugbridge.models.report_filters import ReportFilters


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = AsyncMock()
    return session


@pytest.fixture
def mock_llm():
    """Create a mock XAI LLM."""
    llm = AsyncMock()
    return llm


@pytest.fixture
def sample_report_date():
    """Sample report date (yesterday)."""
    return (datetime.now(UTC) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


@pytest.fixture
def sample_metrics(sample_report_date):
    """Sample DailyMetrics for testing."""
    return DailyMetrics(
        date=sample_report_date,
        new_issues_count=25,
        bugs_count=15,
        feature_requests_count=10,
        bugs_percentage=60.0,
        sentiment_distribution={
            "Positive": 5,
            "Neutral": 10,
            "Negative": 7,
            "Frustrated": 2,
            "Angry": 1,
        },
        priority_items=[
            {
                "title": "Critical bug in payment system",
                "priority_score": 95,
                "priority": "Highest",
                "post_id": "post123",
            },
            {
                "title": "Feature request: Dark mode",
                "priority_score": 70,
                "priority": "High",
                "post_id": "post456",
            },
        ],
        tickets_created=20,
        tickets_resolved=12,
        average_response_time_hours=2.5,
        resolution_rate=60.0,
        average_resolution_time_hours=24.0,
    )


@pytest.fixture
def sample_report_summary():
    """Sample ReportSummary for testing."""
    return ReportSummary(
        executive_summary="Today's feedback activity shows a significant increase in bug reports, with 60% of new issues identified as bugs. The sentiment distribution indicates mostly neutral feedback with some negative sentiment.",
        key_insights=[
            "Bug reports increased by 25% compared to last week",
            "Payment system issues are the top priority",
            "Resolution rate improved to 60%",
        ],
        recommendations=[
            "Investigate payment system bugs immediately",
            "Focus on reducing response time for high-priority issues",
            "Consider implementing dark mode feature based on user requests",
        ],
        summary_text="The daily report indicates a busy day with 25 new issues reported, of which 15 were identified as bugs (60%). The sentiment analysis shows a mix of positive, neutral, and negative feedback. Jira ticket creation and resolution metrics show good progress with a 60% resolution rate and average response time of 2.5 hours.",
    )


@pytest.mark.asyncio
async def test_query_daily_metrics_basic(mock_session, sample_report_date):
    """Test query_daily_metrics with basic date filtering."""
    # Mock query results
    mock_session.execute = AsyncMock()
    
    # New issues count
    mock_result = MagicMock()
    mock_result.scalar.return_value = 25
    mock_session.execute.return_value = mock_result
    
    # Bugs count
    mock_bug_result = MagicMock()
    mock_bug_result.scalar.return_value = 15
    mock_session.execute.side_effect = [
        mock_result,  # new_issues_count
        mock_bug_result,  # bugs_count
        mock_bug_result,  # feature_requests_count (will be calculated)
    ]
    
    # Sentiment distribution
    mock_sentiment_rows = [
        MagicMock(sentiment="Positive", count=5),
        MagicMock(sentiment="Negative", count=7),
    ]
    mock_sentiment_result = MagicMock()
    mock_sentiment_result.__iter__ = lambda self: iter(mock_sentiment_rows)
    mock_session.execute.side_effect = [
        mock_result,  # new_issues_count
        mock_bug_result,  # bugs_count
        mock_bug_result,  # feature_requests_count
        mock_sentiment_result,  # sentiment_query
        MagicMock(scalar=lambda: 20),  # tickets_created
        MagicMock(scalar=lambda: 12),  # tickets_resolved
        MagicMock(scalar=lambda: 2.5),  # average_response_time
        MagicMock(scalar=lambda: 24.0),  # average_resolution_time
        MagicMock(__iter__=lambda self: iter([])),  # priority_items
    ]
    
    metrics = await query_daily_metrics(mock_session, sample_report_date)
    
    assert metrics.new_issues_count == 25
    assert metrics.bugs_count == 15
    assert metrics.feature_requests_count == 10
    assert metrics.bugs_percentage == 60.0


@pytest.mark.asyncio
async def test_query_daily_metrics_with_filters(mock_session, sample_report_date):
    """Test query_daily_metrics with filters applied."""
    filters = ReportFilters(
        board_ids=["board1"],
        tags=["bug", "urgent"],
        bug_only=True,
        min_priority_score=70,
    )
    
    # Mock priority items query
    mock_priority_rows = [
        MagicMock(
            title="Critical bug",
            priority_score=95,
            analysis_data={"recommended_jira_priority": "Highest"},
            canny_post_id="post123",
        ),
    ]
    mock_priority_result = MagicMock()
    mock_priority_result.__iter__ = lambda self: iter(mock_priority_rows)
    
    def mock_execute(query):
        result = MagicMock()
        query_str = str(query)
        
        if "count" in query_str.lower() and "feedback_posts" in query_str.lower():
            result.scalar.return_value = 10
        elif "is_bug" in query_str.lower() and "True" in query_str:
            result.scalar.return_value = 10
        elif "is_bug" in query_str.lower() and "False" in query_str:
            result.scalar.return_value = 0
        elif "sentiment" in query_str.lower():
            return MagicMock(__iter__=lambda self: iter([]))
        elif "jira_tickets" in query_str.lower() and "created_at" in query_str.lower() and "resolved_at" not in query_str.lower():
            result.scalar.return_value = 10
        elif "resolved_at" in query_str.lower():
            result.scalar.return_value = 8
        elif "response_time" in query_str.lower() or "created_at - collected_at" in query_str.lower():
            result.scalar.return_value = 1.5
        elif "resolution_time" in query_str.lower() or "resolved_at - created_at" in query_str.lower():
            result.scalar.return_value = 20.0
        elif "priority_score" in query_str.lower():
            return mock_priority_result
        else:
            result.scalar.return_value = 0
        
        return result
    
    mock_session.execute = AsyncMock(side_effect=mock_execute)
    
    metrics = await query_daily_metrics(mock_session, sample_report_date, filters=filters)
    
    assert metrics.new_issues_count == 10
    assert metrics.bugs_count == 10
    assert metrics.feature_requests_count == 0  # bug_only filter


@pytest.mark.asyncio
async def test_reporting_agent_generate_daily_report(
    mock_llm, mock_session, sample_report_date, sample_metrics, sample_report_summary
):
    """Test ReportingAgent.generate_daily_report with mocked dependencies."""
    with patch("bugbridge.agents.reporting.get_session") as mock_get_session, \
         patch("bugbridge.agents.reporting.query_daily_metrics") as mock_query_metrics, \
         patch("bugbridge.agents.reporting.create_report_prompt") as mock_create_prompt, \
         patch("bugbridge.agents.reporting.format_report_markdown") as mock_format_markdown, \
         patch("bugbridge.agents.reporting.EmailService") as mock_email_service, \
         patch("bugbridge.agents.reporting.FileStorageService") as mock_file_storage, \
         patch("bugbridge.agents.reporting.get_settings") as mock_get_settings:
        
        # Setup mocks
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        mock_query_metrics.return_value = sample_metrics
        mock_create_prompt.return_value = "Test prompt"
        mock_format_markdown.return_value = "# Daily Report\n\nTest content"
        
        # Mock LLM response
        mock_llm_response = MagicMock()
        mock_llm_response.content = sample_report_summary.model_dump_json()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        
        # Mock structured output generation
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=sample_report_summary)
        
        # Mock database operations
        mock_report = Report(
            id=uuid4(),
            report_type="daily",
            report_date=sample_report_date,
            report_content="# Daily Report\n\nTest content",
            metrics=sample_metrics.model_dump(),
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.reporting.email_enabled = False
        mock_settings.reporting.file_storage_enabled = False
        mock_settings.reporting.recipients = []
        mock_get_settings.return_value = mock_settings
        
        # Create agent
        agent = ReportingAgent(llm=mock_llm, deterministic=True)
        
        # Generate report
        result = await agent.generate_daily_report(report_date=sample_report_date)
        
        # Assertions
        assert result["report_id"] is not None
        assert result["report_date"] == sample_report_date
        assert result["metrics"] == sample_metrics.model_dump()
        assert result["summary"] == sample_report_summary.model_dump()
        assert result["content"] == "# Daily Report\n\nTest content"
        
        # Verify database operations
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_reporting_agent_with_filters(mock_llm, mock_session, sample_report_date):
    """Test ReportingAgent.generate_daily_report with filters."""
    filters = ReportFilters(
        start_date=sample_report_date,
        end_date=sample_report_date + timedelta(days=7),
        board_ids=["board1"],
        bug_only=True,
    )
    
    sample_metrics = DailyMetrics(
        date=sample_report_date,
        new_issues_count=10,
        bugs_count=10,
        feature_requests_count=0,
        bugs_percentage=100.0,
        sentiment_distribution={},
        priority_items=[],
        tickets_created=8,
        tickets_resolved=5,
        average_response_time_hours=1.5,
        resolution_rate=62.5,
        average_resolution_time_hours=18.0,
    )
    
    sample_summary = ReportSummary(
        executive_summary="Filtered report showing only bugs from board1 over the past week.",
        key_insights=["All 10 issues were bugs", "Good resolution rate of 62.5%"],
        recommendations=["Continue monitoring bug trends"],
        summary_text="This filtered report focuses on bugs from board1, showing 10 bugs identified with a resolution rate of 62.5%.",
    )
    
    with patch("bugbridge.agents.reporting.get_session") as mock_get_session, \
         patch("bugbridge.agents.reporting.query_daily_metrics") as mock_query_metrics, \
         patch("bugbridge.agents.reporting.create_report_prompt") as mock_create_prompt, \
         patch("bugbridge.agents.reporting.format_report_markdown") as mock_format_markdown, \
         patch("bugbridge.agents.reporting.get_settings") as mock_get_settings:
        
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        mock_query_metrics.return_value = sample_metrics
        mock_create_prompt.return_value = "Test prompt"
        mock_format_markdown.return_value = "# Filtered Report\n\nContent"
        
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=sample_summary)
        
        mock_report = Report(
            id=uuid4(),
            report_type="daily",
            report_date=sample_report_date,
            report_content="# Filtered Report\n\nContent",
            metrics=sample_metrics.model_dump(),
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        mock_settings = MagicMock()
        mock_settings.reporting.email_enabled = False
        mock_settings.reporting.file_storage_enabled = False
        mock_get_settings.return_value = mock_settings
        
        agent = ReportingAgent(llm=mock_llm, deterministic=True)
        result = await agent.generate_daily_report(report_date=sample_report_date, filters=filters)
        
        # Verify filters were passed to query_daily_metrics
        mock_query_metrics.assert_called_once()
        call_args = mock_query_metrics.call_args
        assert call_args[0][1] == sample_report_date
        assert call_args[1]["filters"] == filters
        
        assert result["metrics"]["bugs_count"] == 10
        assert result["metrics"]["feature_requests_count"] == 0


@pytest.mark.asyncio
async def test_reporting_agent_delivery_email(mock_llm, mock_session, sample_report_date):
    """Test ReportingAgent with email delivery enabled."""
    sample_metrics = DailyMetrics(
        date=sample_report_date,
        new_issues_count=5,
        bugs_count=3,
        feature_requests_count=2,
        bugs_percentage=60.0,
        sentiment_distribution={},
        priority_items=[],
        tickets_created=4,
        tickets_resolved=2,
        average_response_time_hours=1.0,
        resolution_rate=50.0,
        average_resolution_time_hours=12.0,
    )
    
    sample_summary = ReportSummary(
        executive_summary="Test summary",
        key_insights=["Test insight"],
        recommendations=[],
        summary_text="Test summary text with enough content to meet the minimum length requirement for the summary_text field.",
    )
    
    with patch("bugbridge.agents.reporting.get_session") as mock_get_session, \
         patch("bugbridge.agents.reporting.query_daily_metrics") as mock_query_metrics, \
         patch("bugbridge.agents.reporting.create_report_prompt") as mock_create_prompt, \
         patch("bugbridge.agents.reporting.format_report_markdown") as mock_format_markdown, \
         patch("bugbridge.agents.reporting.EmailService") as mock_email_service_class, \
         patch("bugbridge.agents.reporting.get_settings") as mock_get_settings:
        
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        mock_query_metrics.return_value = sample_metrics
        mock_create_prompt.return_value = "Test prompt"
        mock_format_markdown.return_value = "# Report\n\nContent"
        
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=sample_summary)
        
        mock_report = Report(
            id=uuid4(),
            report_type="daily",
            report_date=sample_report_date,
            report_content="# Report\n\nContent",
            metrics=sample_metrics.model_dump(),
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock email service
        mock_email_service = MagicMock()
        mock_email_service.send_report_email = MagicMock()
        mock_email_service_class.return_value = mock_email_service
        
        # Mock settings with email enabled
        mock_settings = MagicMock()
        mock_settings.reporting.email_enabled = True
        mock_settings.reporting.file_storage_enabled = False
        mock_settings.reporting.recipients = ["admin@example.com", "team@example.com"]
        mock_settings.email.smtp_host = "smtp.example.com"
        mock_settings.email.smtp_port = 587
        mock_settings.email.smtp_username = "user@example.com"
        mock_settings.email.smtp_password = None
        mock_settings.email.use_tls = True
        mock_settings.email.from_email = "noreply@example.com"
        mock_settings.file_storage.enabled = False
        mock_get_settings.return_value = mock_settings
        
        agent = ReportingAgent(llm=mock_llm, deterministic=True)
        result = await agent.generate_daily_report(report_date=sample_report_date)
        
        # Verify email was sent
        assert result["delivery"]["email"]["success"] is True
        mock_email_service.send_report_email.assert_called_once()
        call_args = mock_email_service.send_report_email.call_args
        assert call_args[1]["to_emails"] == ["admin@example.com", "team@example.com"]


@pytest.mark.asyncio
async def test_reporting_agent_delivery_file_storage(mock_llm, mock_session, sample_report_date):
    """Test ReportingAgent with file storage delivery enabled."""
    sample_metrics = DailyMetrics(
        date=sample_report_date,
        new_issues_count=5,
        bugs_count=3,
        feature_requests_count=2,
        bugs_percentage=60.0,
        sentiment_distribution={},
        priority_items=[],
        tickets_created=4,
        tickets_resolved=2,
        average_response_time_hours=1.0,
        resolution_rate=50.0,
        average_resolution_time_hours=12.0,
    )
    
    sample_summary = ReportSummary(
        executive_summary="Test summary",
        key_insights=["Test insight"],
        recommendations=[],
        summary_text="Test summary text with enough content to meet the minimum length requirement for the summary_text field.",
    )
    
    with patch("bugbridge.agents.reporting.get_session") as mock_get_session, \
         patch("bugbridge.agents.reporting.query_daily_metrics") as mock_query_metrics, \
         patch("bugbridge.agents.reporting.create_report_prompt") as mock_create_prompt, \
         patch("bugbridge.agents.reporting.format_report_markdown") as mock_format_markdown, \
         patch("bugbridge.agents.reporting.FileStorageService") as mock_file_storage_class, \
         patch("bugbridge.agents.reporting.get_settings") as mock_get_settings:
        
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        mock_query_metrics.return_value = sample_metrics
        mock_create_prompt.return_value = "Test prompt"
        mock_format_markdown.return_value = "# Report\n\nContent"
        
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=sample_summary)
        
        mock_report = Report(
            id=uuid4(),
            report_type="daily",
            report_date=sample_report_date,
            report_content="# Report\n\nContent",
            metrics=sample_metrics.model_dump(),
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock file storage service
        mock_file_storage = MagicMock()
        mock_file_storage.save_report.return_value = "./reports/2025/01/report_2025-01-15_abc123.md"
        mock_file_storage_class.return_value = mock_file_storage
        
        # Mock settings with file storage enabled
        mock_settings = MagicMock()
        mock_settings.reporting.email_enabled = False
        mock_settings.reporting.file_storage_enabled = True
        mock_settings.reporting.recipients = []
        mock_settings.file_storage.enabled = True
        mock_settings.file_storage.base_path = "./reports"
        mock_settings.file_storage.create_dirs = True
        mock_get_settings.return_value = mock_settings
        
        agent = ReportingAgent(llm=mock_llm, deterministic=True)
        result = await agent.generate_daily_report(report_date=sample_report_date)
        
        # Verify file was saved
        assert result["delivery"]["file_storage"]["success"] is True
        assert "file_path" in result["delivery"]["file_storage"]
        mock_file_storage.save_report.assert_called_once()


@pytest.mark.asyncio
async def test_reporting_agent_delivery_error_handling(mock_llm, mock_session, sample_report_date):
    """Test ReportingAgent handles delivery errors gracefully."""
    sample_metrics = DailyMetrics(
        date=sample_report_date,
        new_issues_count=5,
        bugs_count=3,
        feature_requests_count=2,
        bugs_percentage=60.0,
        sentiment_distribution={},
        priority_items=[],
        tickets_created=4,
        tickets_resolved=2,
        average_response_time_hours=1.0,
        resolution_rate=50.0,
        average_resolution_time_hours=12.0,
    )
    
    sample_summary = ReportSummary(
        executive_summary="Test summary",
        key_insights=["Test insight"],
        recommendations=[],
        summary_text="Test summary text with enough content to meet the minimum length requirement for the summary_text field.",
    )
    
    with patch("bugbridge.agents.reporting.get_session") as mock_get_session, \
         patch("bugbridge.agents.reporting.query_daily_metrics") as mock_query_metrics, \
         patch("bugbridge.agents.reporting.create_report_prompt") as mock_create_prompt, \
         patch("bugbridge.agents.reporting.format_report_markdown") as mock_format_markdown, \
         patch("bugbridge.agents.reporting.EmailService") as mock_email_service_class, \
         patch("bugbridge.agents.reporting.get_settings") as mock_get_settings:
        
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        mock_query_metrics.return_value = sample_metrics
        mock_create_prompt.return_value = "Test prompt"
        mock_format_markdown.return_value = "# Report\n\nContent"
        
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=sample_summary)
        
        mock_report = Report(
            id=uuid4(),
            report_type="daily",
            report_date=sample_report_date,
            report_content="# Report\n\nContent",
            metrics=sample_metrics.model_dump(),
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        # Mock email service to raise error
        mock_email_service = MagicMock()
        mock_email_service.send_report_email.side_effect = Exception("SMTP connection failed")
        mock_email_service_class.return_value = mock_email_service
        
        # Mock settings with email enabled
        mock_settings = MagicMock()
        mock_settings.reporting.email_enabled = True
        mock_settings.reporting.file_storage_enabled = False
        mock_settings.reporting.recipients = ["admin@example.com"]
        mock_settings.email.smtp_host = "smtp.example.com"
        mock_settings.email.smtp_port = 587
        mock_settings.email.smtp_username = "user@example.com"
        mock_settings.email.smtp_password = None
        mock_settings.email.use_tls = True
        mock_settings.email.from_email = "noreply@example.com"
        mock_get_settings.return_value = mock_settings
        
        agent = ReportingAgent(llm=mock_llm, deterministic=True)
        result = await agent.generate_daily_report(report_date=sample_report_date)
        
        # Verify report was still generated despite delivery error
        assert result["report_id"] is not None
        assert result["delivery"]["email"]["success"] is False
        assert "error" in result["delivery"]["email"]
        assert "SMTP" in result["delivery"]["email"]["error"]


def test_create_report_prompt(sample_metrics):
    """Test create_report_prompt generates correct prompt."""
    prompt = create_report_prompt(sample_metrics)
    
    assert "data analyst" in prompt.lower()
    assert str(sample_metrics.new_issues_count) in prompt
    assert str(sample_metrics.bugs_count) in prompt
    assert str(sample_metrics.tickets_created) in prompt
    assert "Executive Summary" in prompt
    assert "Key Insights" in prompt
    assert "Recommendations" in prompt


def test_format_report_markdown(sample_metrics, sample_report_summary):
    """Test format_report_markdown generates correct Markdown."""
    markdown = format_report_markdown(sample_metrics, sample_report_summary)
    
    assert "# Daily Summary Report" in markdown
    assert "## Metrics" in markdown
    assert str(sample_metrics.new_issues_count) in markdown
    assert str(sample_metrics.bugs_count) in markdown
    assert sample_report_summary.executive_summary in markdown
    assert "## Key Insights" in markdown
    assert "## Recommendations" in markdown


def test_get_reporting_agent():
    """Test get_reporting_agent factory function."""
    agent1 = get_reporting_agent()
    agent2 = get_reporting_agent()
    
    # Should return the same instance (singleton pattern)
    assert agent1 is agent2
    assert isinstance(agent1, ReportingAgent)


@pytest.mark.asyncio
async def test_reporting_agent_default_date(mock_llm, mock_session):
    """Test ReportingAgent uses yesterday as default date."""
    sample_metrics = DailyMetrics(
        date=datetime.now(UTC) - timedelta(days=1),
        new_issues_count=5,
        bugs_count=3,
        feature_requests_count=2,
        bugs_percentage=60.0,
        sentiment_distribution={},
        priority_items=[],
        tickets_created=4,
        tickets_resolved=2,
        average_response_time_hours=1.0,
        resolution_rate=50.0,
        average_resolution_time_hours=12.0,
    )
    
    sample_summary = ReportSummary(
        executive_summary="Test summary",
        key_insights=["Test insight"],
        recommendations=[],
        summary_text="Test summary text with enough content to meet the minimum length requirement for the summary_text field.",
    )
    
    with patch("bugbridge.agents.reporting.get_session") as mock_get_session, \
         patch("bugbridge.agents.reporting.query_daily_metrics") as mock_query_metrics, \
         patch("bugbridge.agents.reporting.create_report_prompt") as mock_create_prompt, \
         patch("bugbridge.agents.reporting.format_report_markdown") as mock_format_markdown, \
         patch("bugbridge.agents.reporting.get_settings") as mock_get_settings:
        
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_get_session.return_value.__aexit__.return_value = None
        
        mock_query_metrics.return_value = sample_metrics
        mock_create_prompt.return_value = "Test prompt"
        mock_format_markdown.return_value = "# Report\n\nContent"
        
        mock_llm.with_structured_output = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=sample_summary)
        
        mock_report = Report(
            id=uuid4(),
            report_type="daily",
            report_date=sample_metrics.date,
            report_content="# Report\n\nContent",
            metrics=sample_metrics.model_dump(),
        )
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        
        mock_settings = MagicMock()
        mock_settings.reporting.email_enabled = False
        mock_settings.reporting.file_storage_enabled = False
        mock_get_settings.return_value = mock_settings
        
        agent = ReportingAgent(llm=mock_llm, deterministic=True)
        result = await agent.generate_daily_report(report_date=None)
        
        # Verify query was called with yesterday's date
        call_args = mock_query_metrics.call_args
        called_date = call_args[0][1]
        expected_date = (datetime.now(UTC) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert called_date.date() == expected_date.date()

