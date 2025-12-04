"""
Jira Creation Agent

Creates Jira tickets from analyzed feedback posts, formatting tickets with
all analysis results and linking back to Canny.io feedback.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, List, Literal, Optional

from bugbridge.agents.base import BaseAgent
from bugbridge.config import JiraSettings, get_settings
from bugbridge.integrations.mcp_jira import (
    MCPJiraClient,
    MCPJiraError,
    MCPJiraAuthenticationError,
    MCPJiraValidationError,
    MCPJiraConnectionError,
    MCPJiraRateLimitError,
    MCPJiraNotFoundError,
)
from bugbridge.utils.assignment import get_assignment_manager
from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.jira import JiraTicketCreate
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


def map_priority_score_to_jira_priority(priority_score: Optional[int]) -> Literal["Critical", "High", "Medium", "Low"]:
    """
    Map priority score (1-100) to Jira priority level.

    Args:
        priority_score: Priority score from analysis (1-100, None if not available).

    Returns:
        Jira priority level (Critical, High, Medium, Low).
    """
    if priority_score is None:
        return "Medium"

    if priority_score >= 80:
        return "Critical"
    elif priority_score >= 60:
        return "High"
    elif priority_score >= 40:
        return "Medium"
    else:
        return "Low"


def determine_issue_type(bug_detection: Optional[BugDetectionResult]) -> Literal["Bug", "Story", "Task"]:
    """
    Determine Jira issue type based on bug detection result.

    Args:
        bug_detection: Bug detection analysis results.

    Returns:
        Jira issue type (Bug, Story, or Task).
    
    Note: For Next-Gen Jira projects, only Task and Epic are supported.
    We always return "Task" regardless of bug detection results.
    """
    # Next-Gen Jira projects typically only support Task and Epic issue types
    # Return "Task" for both bugs and feature requests
    return "Task"


def generate_labels(
    bug_detection: Optional[BugDetectionResult],
    sentiment_analysis: Optional[SentimentAnalysisResult],
    priority_score: Optional[PriorityScoreResult],
    feedback_post: FeedbackPost,
) -> List[str]:
    """
    Generate labels for Jira ticket based on analysis results.

    Args:
        bug_detection: Bug detection analysis results.
        sentiment_analysis: Sentiment analysis results.
        priority_score: Priority scoring results.
        feedback_post: Original feedback post.

    Returns:
        List of labels to apply to the Jira ticket.
    """
    labels: List[str] = ["bugbridge", "canny-feedback"]

    # Add bug/feature label
    if bug_detection:
        if bug_detection.is_bug:
            labels.append("bug")
            if bug_detection.bug_severity and bug_detection.bug_severity != "N/A":
                labels.append(f"severity-{bug_detection.bug_severity.lower()}")
        else:
            labels.append("feature-request")

    # Add sentiment label
    if sentiment_analysis:
        sentiment_lower = sentiment_analysis.sentiment.lower()
        labels.append(f"sentiment-{sentiment_lower}")
        if sentiment_analysis.urgency:
            labels.append(f"urgency-{sentiment_analysis.urgency.lower()}")

    # Add priority/burning issue labels
    if priority_score:
        if priority_score.is_burning_issue:
            labels.append("burning-issue")
        if priority_score.priority_score:
            if priority_score.priority_score >= 80:
                labels.append("critical-priority")
            elif priority_score.priority_score >= 60:
                labels.append("high-priority")

    # Add tags from Canny.io post
    if feedback_post.tags:
        # Sanitize tags (remove spaces, special chars that might break Jira)
        for tag in feedback_post.tags:
            sanitized = tag.lower().replace(" ", "-").replace("_", "-")
            # Remove any non-alphanumeric except hyphens
            sanitized = "".join(c if c.isalnum() or c == "-" else "" for c in sanitized)
            if sanitized and sanitized not in labels:
                labels.append(f"canny-{sanitized}")

    return labels


def format_jira_description(
    feedback_post: FeedbackPost,
    bug_detection: Optional[BugDetectionResult],
    sentiment_analysis: Optional[SentimentAnalysisResult],
    priority_score: Optional[PriorityScoreResult],
) -> str:
    """
    Format Jira ticket description from feedback and analysis results.

    Args:
        feedback_post: Original feedback post from Canny.io.
        bug_detection: Bug detection analysis results.
        sentiment_analysis: Sentiment analysis results.
        priority_score: Priority scoring results.

    Returns:
        Formatted description text (Markdown format).
    """
    description_parts: List[str] = []

    # Header
    description_parts.append("## Feedback Summary")
    description_parts.append("")
    description_parts.append(f"**Original Feedback:** {feedback_post.title}")
    description_parts.append("")
    description_parts.append(feedback_post.content)
    description_parts.append("")

    # Author and Engagement
    description_parts.append("## Feedback Metadata")
    description_parts.append("")
    description_parts.append(f"- **Author:** {feedback_post.author_name or feedback_post.author_id or 'Unknown'}")
    description_parts.append(f"- **Votes:** {feedback_post.votes}")
    description_parts.append(f"- **Comments:** {feedback_post.comments_count}")
    if feedback_post.url:
        description_parts.append(f"- **Canny.io Post:** {feedback_post.url}")
    description_parts.append("")

    # Analysis Results
    description_parts.append("## Analysis Results")
    description_parts.append("")

    # Bug Detection
    if bug_detection:
        description_parts.append("### Bug Detection")
        description_parts.append("")
        description_parts.append(f"- **Classification:** {'Bug' if bug_detection.is_bug else 'Feature Request'}")
        if bug_detection.bug_severity and bug_detection.bug_severity != "N/A":
            description_parts.append(f"- **Severity:** {bug_detection.bug_severity}")
        description_parts.append(f"- **Confidence:** {bug_detection.confidence:.2f}")
        description_parts.append(f"- **Reasoning:** {bug_detection.reasoning}")
        description_parts.append("")

    # Sentiment Analysis
    if sentiment_analysis:
        description_parts.append("### Sentiment Analysis")
        description_parts.append("")
        description_parts.append(f"- **Sentiment:** {sentiment_analysis.sentiment}")
        description_parts.append(f"- **Sentiment Score:** {sentiment_analysis.sentiment_score:.2f}")
        description_parts.append(f"- **Urgency:** {sentiment_analysis.urgency}")
        if sentiment_analysis.emotions_detected:
            emotions_str = ", ".join(sentiment_analysis.emotions_detected)
            description_parts.append(f"- **Emotions Detected:** {emotions_str}")
        description_parts.append(f"- **Reasoning:** {sentiment_analysis.reasoning}")
        description_parts.append("")

    # Priority Scoring
    if priority_score:
        description_parts.append("### Priority Scoring")
        description_parts.append("")
        description_parts.append(f"- **Priority Score:** {priority_score.priority_score}/100")
        description_parts.append(f"- **Burning Issue:** {'Yes' if priority_score.is_burning_issue else 'No'}")
        description_parts.append(f"- **Engagement Score:** {priority_score.engagement_score:.2f}")
        description_parts.append(f"- **Reasoning:** {priority_score.priority_reasoning}")
        description_parts.append("")

    # Join all parts
    return "\n".join(description_parts)


def format_jira_summary(
    feedback_post: FeedbackPost,
    bug_detection: Optional[BugDetectionResult],
) -> str:
    """
    Format Jira ticket summary/title from feedback post.

    Args:
        feedback_post: Original feedback post from Canny.io.
        bug_detection: Bug detection analysis results (to add [Bug] prefix).

    Returns:
        Formatted summary text (max 255 characters for Jira).
    """
    # Add prefix based on bug detection
    # Note: For Next-Gen projects, we use Task type for everything
    # But we still differentiate in the summary for clarity
    if bug_detection and bug_detection.is_bug:
        prefix = "[Bug] "
    else:
        prefix = "[Feature] "

    # Use feedback title as base
    summary = feedback_post.title.strip()

    # Combine prefix and title, truncate if needed (Jira max is 255)
    full_summary = prefix + summary
    if len(full_summary) > 255:
        # Truncate title to fit prefix
        max_title_length = 255 - len(prefix)
        summary = summary[:max_title_length].rstrip()
        full_summary = prefix + summary

    return full_summary


class JiraCreationAgent(BaseAgent):
    """
    Agent for creating Jira tickets from analyzed feedback posts.

    Formats tickets with all analysis results, maps priority scores to Jira priorities,
    determines issue types, generates labels, and creates tickets via MCP Jira client.
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        deterministic: bool = True,
        jira_client: Optional[MCPJiraClient] = None,
    ):
        """
        Initialize Jira Creation Agent.

        Args:
            llm: Optional XAI LLM instance (not used for ticket creation, but kept for consistency).
            deterministic: Whether to enforce deterministic behavior.
            jira_client: Optional MCPJiraClient instance (creates one if not provided).
        """
        super().__init__(
            name="jira_creation_agent",
            llm=llm,
            deterministic=deterministic,
        )
        self._jira_client = jira_client
        self._settings: Optional[JiraSettings] = None

    def _get_jira_client(self) -> MCPJiraClient:
        """
        Get or create MCPJiraClient instance.

        Returns:
            MCPJiraClient instance.
        """
        if self._jira_client:
            return self._jira_client

        # Load settings if not already loaded
        if not self._settings:
            try:
                settings = get_settings()
                self._settings = settings.jira
            except Exception as e:
                logger.warning(f"Could not load Jira settings: {e}")
                raise ValueError(
                    "Jira settings not available. Provide jira_client explicitly or configure JIRA__SERVER_URL and JIRA__PROJECT_KEY."
                ) from e

        # Create client from settings
        return MCPJiraClient(
            server_url=str(self._settings.server_url),
            project_key=self._settings.project_key,
            auto_connect=True,
        )

    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """
        Execute Jira ticket creation from analyzed feedback.

        Args:
            state: Current workflow state containing feedback_post, bug_detection, sentiment_analysis, and priority_score.

        Returns:
            Updated workflow state with jira_ticket_id, jira_ticket_url, and workflow_status.
        """
        # Validate required state
        feedback_post = state.get("feedback_post")
        if not feedback_post:
            error_msg = "Jira Creation Agent requires feedback_post in state"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Ensure feedback_post is a FeedbackPost object
        if isinstance(feedback_post, dict):
            feedback_post = FeedbackPost.model_validate(feedback_post)

        # Get analysis results
        bug_detection = state.get("bug_detection")
        if bug_detection and isinstance(bug_detection, dict):
            bug_detection = BugDetectionResult.model_validate(bug_detection)

        sentiment_analysis = state.get("sentiment_analysis")
        if sentiment_analysis and isinstance(sentiment_analysis, dict):
            sentiment_analysis = SentimentAnalysisResult.model_validate(sentiment_analysis)

        priority_score = state.get("priority_score")
        if priority_score and isinstance(priority_score, dict):
            priority_score = PriorityScoreResult.model_validate(priority_score)

        # Get settings for project key
        try:
            settings = get_settings()
            jira_settings = settings.jira
            project_key = jira_settings.project_key
        except Exception as e:
            error_msg = f"Failed to load Jira settings: {str(e)}"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Format ticket content
        summary = format_jira_summary(feedback_post, bug_detection)
        description = format_jira_description(
            feedback_post,
            bug_detection,
            sentiment_analysis,
            priority_score,
        )

        # Determine issue type and priority
        issue_type = determine_issue_type(bug_detection)
        jira_priority = map_priority_score_to_jira_priority(
            priority_score.priority_score if priority_score else None
        )

        # Generate labels
        labels = generate_labels(
            bug_detection,
            sentiment_analysis,
            priority_score,
            feedback_post,
        )

        # Extract scores for ticket metadata
        sentiment_score = sentiment_analysis.sentiment_score if sentiment_analysis else None
        priority_score_value = priority_score.priority_score if priority_score else None

        # Determine assignee based on assignment strategy
        assignment_manager = get_assignment_manager()
        assignee = assignment_manager.get_assignee(
            components=[],  # Components could be extracted from labels or analysis in the future
            priority=jira_priority,
            labels=labels,  # Labels may contain component hints (e.g., "canny-frontend", "component-api")
        )

        # Create ticket data
        ticket_data = JiraTicketCreate(
            project_key=project_key,
            summary=summary,
            description=description,
            issue_type=issue_type,
            priority=jira_priority,
            labels=labels,
            assignee=assignee,
            sentiment_score=sentiment_score,
            priority_score=priority_score_value,
            canny_post_url=feedback_post.url,
            metadata={
                "burning_issue": priority_score.is_burning_issue if priority_score else False,
                "engagement": {
                    "votes": feedback_post.votes,
                    "comments": feedback_post.comments_count,
                },
                "bug_severity": bug_detection.bug_severity if bug_detection else None,
                "sentiment": sentiment_analysis.sentiment if sentiment_analysis else None,
            },
        )

        # Get Jira client
        jira_client = self._get_jira_client()

        # Create ticket via MCP
        try:
            logger.info(
                f"Creating Jira ticket for feedback post {feedback_post.post_id}",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "issue_type": issue_type,
                    "priority": jira_priority,
                },
            )

            # Use connection context manager
            async with jira_client.connection():
                ticket = await jira_client.create_issue(ticket_data)

            # Log successful creation
            self.log_agent_action(
                "jira_ticket_created",
                {
                    "ticket_key": ticket.key,
                    "ticket_url": ticket.url,
                    "issue_type": issue_type,
                    "priority": jira_priority,
                },
                state,
            )

            # Update workflow state
            updated_state = {
                **state,
                "jira_ticket_id": ticket.key,
                "jira_ticket_url": ticket.url,
                "jira_ticket_status": ticket.status,
                "workflow_status": "ticket_created",
            }

            # Update timestamp
            updated_state = self.update_state_timestamp(updated_state, "ticket_created_at")

            logger.info(
                f"Successfully created Jira ticket {ticket.key} for feedback post {feedback_post.post_id}",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "ticket_key": ticket.key,
                    "ticket_url": ticket.url,
                },
            )

            return updated_state

        except MCPJiraAuthenticationError as e:
            error_msg = f"Jira authentication failed: {str(e)}. Please check Jira credentials."
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "tool_name": e.tool_name,
                    "error_type": "authentication",
                },
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)

        except MCPJiraValidationError as e:
            error_msg = f"Jira ticket validation failed: {str(e)}. Check ticket data format."
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "tool_name": e.tool_name,
                    "error_type": "validation",
                },
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)

        except MCPJiraRateLimitError as e:
            retry_msg = f" (retry after {e.retry_after}s)" if e.retry_after else ""
            error_msg = f"Jira rate limit exceeded: {str(e)}{retry_msg}. Operation will be retried automatically."
            logger.warning(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "tool_name": e.tool_name,
                    "error_type": "rate_limit",
                    "retry_after": e.retry_after,
                },
            )
            # Rate limit errors will be retried by the retry decorator
            # If retries are exhausted, we'll fall through to the generic handler
            return self.add_state_error(state, error_msg)

        except MCPJiraConnectionError as e:
            error_msg = f"Jira connection failed: {str(e)}. Check network connectivity and MCP server status."
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "tool_name": e.tool_name,
                    "error_type": "connection",
                },
                exc_info=True,
            )
            # Connection errors will be retried by the retry decorator
            # If retries are exhausted, return error state
            return self.add_state_error(state, error_msg)

        except MCPJiraError as e:
            error_msg = f"Failed to create Jira ticket: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "tool_name": e.tool_name,
                    "error_type": "generic",
                    "is_retryable": getattr(e, "is_retryable", True),
                },
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)

        except Exception as e:
            error_msg = f"Unexpected error creating Jira ticket: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "error_type": "unexpected",
                },
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)


async def create_jira_ticket_node(state: BugBridgeState) -> BugBridgeState:
    """
    LangGraph node function for Jira Creation Agent.

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with Jira ticket information.
    """
    agent = JiraCreationAgent()
    return await agent.run(state)

