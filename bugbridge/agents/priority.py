"""
Priority Scoring Agent

Calculates priority scores for feedback posts based on multiple factors:
bug severity, sentiment, user engagement, and business impact using
XAI LLM with structured outputs for deterministic priority calculation.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from bugbridge.agents.base import BaseAgent
from bugbridge.models.analysis import BugDetectionResult, PriorityScoreResult, SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.tools.engagement_tools import calculate_engagement_score
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


# System message for priority scoring specialist role
PRIORITY_SCORING_SYSTEM_MESSAGE = """You are a priority scoring specialist with expertise in calculating priority scores 
for customer feedback based on multiple weighted factors. Your scoring should be consistent, balanced, and consider:

Priority Factors (in order of importance):
1. Bug Severity: Critical bugs should score 80-100, High bugs 60-80, Medium 40-60, Low 20-40
2. Sentiment & Urgency: Frustrated/Angry + High urgency = high priority. Positive sentiment = lower priority unless bug
3. User Engagement: High votes/comments indicate broader impact and user concern
4. Business Impact: Keywords indicating revenue impact, security, compliance, core functionality

Priority Score Ranges:
- 90-100: Critical bugs, burning issues, blocking problems affecting many users
- 70-89: High priority bugs, significant user impact, urgent issues
- 50-69: Medium-high priority, important but not blocking
- 30-49: Medium priority, should be addressed in normal course
- 1-29: Low priority, nice-to-have features, minor issues

Burning Issue Criteria (is_burning_issue = true):
- Critical bugs with high engagement OR high urgency sentiment
- High priority bugs with very negative sentiment (Frustrated/Angry) AND high urgency
- Any issue with exceptional engagement (top 5% of posts) AND negative sentiment
- Security vulnerabilities or data loss risks regardless of engagement

Jira Priority Mapping:
- Critical (90-100): Critical priority in Jira
- High (70-89): High priority in Jira
- Medium (50-69): Medium priority in Jira
- Low (1-49): Low priority in Jira

Provide clear, structured analysis with detailed reasoning for the priority score."""


def calculate_engagement_score_from_post(feedback_post: FeedbackPost) -> float:
    """
    Calculate engagement score from feedback post.

    Args:
        feedback_post: Feedback post with votes and comments.

    Returns:
        Engagement score (0.0 to ~100.0).
    """
    # Calculate days since creation for recency weighting
    now = datetime.now(UTC)
    if isinstance(feedback_post.created_at, datetime):
        days_since_creation = (now - feedback_post.created_at.replace(tzinfo=UTC)).total_seconds() / 86400
    else:
        days_since_creation = None

    return calculate_engagement_score(
        votes=feedback_post.votes,
        comments_count=feedback_post.comments_count,
        days_since_creation=days_since_creation,
    )


def create_priority_scoring_prompt(
    feedback_post: FeedbackPost,
    bug_detection: Optional[BugDetectionResult],
    sentiment_analysis: Optional[SentimentAnalysisResult],
    engagement_score: float,
    sentiment_weight: float = 0.3,
    bug_severity_weight: float = 0.5,
) -> str:
    """
    Create prompt for priority scoring analysis.

    Args:
        feedback_post: Feedback post to score.
        bug_detection: Bug detection results (if available).
        sentiment_analysis: Sentiment analysis results (if available).
        engagement_score: Calculated engagement score.
        sentiment_weight: Weight for sentiment factor (default: 0.3).
        bug_severity_weight: Weight for bug severity factor (default: 0.5).

    Returns:
        Formatted prompt string.
    """
    # Build bug detection summary
    bug_summary = "No bug detection analysis available"
    if bug_detection:
        bug_summary = (
            f"Bug: {'Yes' if bug_detection.is_bug else 'No'}, "
            f"Severity: {bug_detection.bug_severity}, "
            f"Confidence: {bug_detection.confidence:.2f}, "
            f"Keywords: {', '.join(bug_detection.keywords_identified[:5])}"
        )

    # Build sentiment summary
    sentiment_summary = "No sentiment analysis available"
    if sentiment_analysis:
        sentiment_summary = (
            f"Sentiment: {sentiment_analysis.sentiment}, "
            f"Score: {sentiment_analysis.sentiment_score:.2f}, "
            f"Urgency: {sentiment_analysis.urgency}, "
            f"Emotions: {', '.join(sentiment_analysis.emotions_detected[:5])}"
        )

    # Calculate days since creation
    now = datetime.now(UTC)
    if isinstance(feedback_post.created_at, datetime):
        days_since = (now - feedback_post.created_at.replace(tzinfo=UTC)).days
        recency = f"{days_since} days ago"
    else:
        recency = "unknown"

    prompt = f"""Calculate a priority score (1-100) for the following feedback considering multiple weighted factors.

Feedback Post:
Title: {feedback_post.title}
Content: {feedback_post.content}

Post Metadata:
- Votes: {feedback_post.votes}
- Comments: {feedback_post.comments_count}
- Engagement Score: {engagement_score:.2f}
- Status: {feedback_post.status}
- Tags: {', '.join(feedback_post.tags) if feedback_post.tags else 'None'}
- Created: {feedback_post.created_at} ({recency})

Bug Detection Analysis:
{bug_summary}

Sentiment Analysis:
{sentiment_summary}

Priority Calculation Weights:
- Bug Severity Weight: {bug_severity_weight:.2f}
- Sentiment Weight: {sentiment_weight:.2f}
- Engagement Weight: {1.0 - bug_severity_weight - sentiment_weight:.2f}

Factors to consider (in priority order):
1. Bug severity (if bug detected): Critical/High bugs need immediate attention
2. Sentiment & urgency: Frustrated/Angry + High urgency = higher priority
3. User engagement: High votes/comments indicate broader user concern
4. Business impact keywords: Revenue, security, compliance, core functionality
5. Recency: Newer issues may need faster response (already factored into engagement)

Provide a structured analysis with:
- priority_score: int (1-100) where higher = more important
- is_burning_issue: boolean (true if requires immediate attention based on criteria)
- priority_reasoning: detailed explanation of how the score was calculated, including factor weights
- recommended_jira_priority: Critical|High|Medium|Low (based on score ranges)
- engagement_score: float (use the provided engagement score: {engagement_score:.2f})
- sentiment_weight: float (use provided weight: {sentiment_weight:.2f})
- bug_severity_weight: float (use provided weight: {bug_severity_weight:.2f})

Burning Issue Detection:
Flag as burning issue (is_burning_issue = true) if ANY of:
- Critical bugs with high engagement (engagement_score > 15) OR high urgency sentiment
- High priority bugs (severity High) with Frustrated/Angry sentiment AND High urgency
- Exceptional engagement (engagement_score > 25) AND negative sentiment (Negative/Frustrated/Angry)
- Security/data loss indicators regardless of engagement

Be thorough and consistent in your analysis."""
    return prompt


def is_burning_issue(
    bug_detection: Optional[BugDetectionResult],
    sentiment_analysis: Optional[SentimentAnalysisResult],
    engagement_score: float,
) -> bool:
    """
    Determine if feedback post is a burning issue based on heuristics.

    This is a deterministic check that can be used to validate or supplement LLM output.

    Args:
        bug_detection: Bug detection results.
        sentiment_analysis: Sentiment analysis results.
        engagement_score: Calculated engagement score.

    Returns:
        True if this is a burning issue, False otherwise.
    """
    # Critical bugs with high engagement or high urgency
    if bug_detection and bug_detection.is_bug:
        if bug_detection.bug_severity == "Critical":
            if engagement_score > 15:
                return True
            if sentiment_analysis and sentiment_analysis.urgency == "High":
                return True

        # High severity bugs with negative sentiment and high urgency
        if bug_detection.bug_severity == "High":
            if sentiment_analysis:
                if sentiment_analysis.sentiment in ["Frustrated", "Angry"] and sentiment_analysis.urgency == "High":
                    return True

    # Exceptional engagement with negative sentiment
    if engagement_score > 25:
        if sentiment_analysis:
            if sentiment_analysis.sentiment in ["Negative", "Frustrated", "Angry"]:
                return True

    return False


class PriorityScoringAgent(BaseAgent):
    """
    Agent for calculating priority scores for feedback posts.

    Uses XAI LLM with structured outputs to calculate priority scores based on
    bug severity, sentiment, user engagement, and other factors.
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        deterministic: bool = True,
        sentiment_weight: float = 0.3,
        bug_severity_weight: float = 0.5,
    ):
        """
        Initialize Priority Scoring Agent.

        Args:
            llm: Optional XAI LLM instance (creates one if not provided).
            deterministic: Whether to enforce deterministic behavior (temperature=0).
            sentiment_weight: Weight for sentiment factor (default: 0.3).
            bug_severity_weight: Weight for bug severity factor (default: 0.5).
        """
        super().__init__(
            name="priority_scoring_agent",
            llm=llm,
            deterministic=deterministic,
        )
        self.sentiment_weight = sentiment_weight
        self.bug_severity_weight = bug_severity_weight

        # Validate weights sum to <= 1.0
        engagement_weight = 1.0 - sentiment_weight - bug_severity_weight
        if engagement_weight < 0:
            raise ValueError(
                f"Priority weights invalid: sentiment_weight ({sentiment_weight}) + "
                f"bug_severity_weight ({bug_severity_weight}) must be <= 1.0"
            )

    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """
        Execute priority scoring analysis on feedback post.

        Args:
            state: Current workflow state containing feedback_post, bug_detection, and sentiment_analysis.

        Returns:
            Updated workflow state with priority_score results.
        """
        # Validate that feedback post exists
        feedback_post = state.get("feedback_post")
        if not feedback_post:
            error_msg = "Priority Scoring Agent requires feedback_post in state"
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

        logger.info(
            f"Starting priority scoring for post: {feedback_post.post_id}",
            extra={
                "agent_name": self.name,
                "post_id": feedback_post.post_id,
                "has_bug_detection": bug_detection is not None,
                "has_sentiment": sentiment_analysis is not None,
            },
        )

        try:
            # Calculate engagement score
            engagement_score = calculate_engagement_score_from_post(feedback_post)

            # Create prompt
            prompt = create_priority_scoring_prompt(
                feedback_post=feedback_post,
                bug_detection=bug_detection,
                sentiment_analysis=sentiment_analysis,
                engagement_score=engagement_score,
                sentiment_weight=self.sentiment_weight,
                bug_severity_weight=self.bug_severity_weight,
            )

            # Log the decision to analyze
            self.log_agent_decision(
                decision="calculate_priority",
                reasoning=f"Calculating priority score for post {feedback_post.post_id} "
                f"with engagement={engagement_score:.2f}",
                state=state,
            )

            # Generate structured output using XAI LLM
            result = await self.generate_structured_output(
                prompt=prompt,
                schema=PriorityScoreResult,
                system_message=PRIORITY_SCORING_SYSTEM_MESSAGE,
            )

            # Ensure calculated_at timestamp is set
            if not result.calculated_at:
                result.calculated_at = datetime.now(UTC)

            # Ensure engagement_score matches our calculation
            result.engagement_score = engagement_score

            # Ensure weights match our configuration
            result.sentiment_weight = self.sentiment_weight
            result.bug_severity_weight = self.bug_severity_weight

            # Validate burning issue detection with heuristics
            heuristic_burning = is_burning_issue(bug_detection, sentiment_analysis, engagement_score)
            if heuristic_burning and not result.is_burning_issue:
                logger.warning(
                    f"Heuristic suggests burning issue but LLM did not flag it for post {feedback_post.post_id}",
                    extra={
                        "agent_name": self.name,
                        "post_id": feedback_post.post_id,
                    },
                )

            # Update state with priority score results
            updated_state = {
                **state,
                "priority_score": result,
            }

            # Update workflow status
            updated_state["workflow_status"] = "analyzed"

            # Add timestamp
            updated_state = self.update_state_timestamp(updated_state, "priority_calculated")

            # Log successful analysis
            self.log_agent_action(
                action="priority_scoring",
                result="success",
                state=updated_state,
                context={
                    "priority_score": result.priority_score,
                    "is_burning_issue": result.is_burning_issue,
                    "jira_priority": result.recommended_jira_priority,
                    "engagement_score": engagement_score,
                },
            )

            logger.info(
                f"Priority scoring completed: score={result.priority_score}, "
                f"burning_issue={result.is_burning_issue}, jira_priority={result.recommended_jira_priority}",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "priority_score": result.priority_score,
                    "is_burning_issue": result.is_burning_issue,
                    "jira_priority": result.recommended_jira_priority,
                },
            )

            return updated_state

        except Exception as e:
            error_msg = f"Priority scoring failed: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                },
                exc_info=True,
            )

            # Update state with error
            return self.add_state_error(state, error_msg)


# Global agent instance (can be reused)
_priority_scoring_agent: Optional[PriorityScoringAgent] = None


def get_priority_scoring_agent(
    sentiment_weight: Optional[float] = None,
    bug_severity_weight: Optional[float] = None,
) -> PriorityScoringAgent:
    """
    Get or create the global Priority Scoring Agent instance.

    Args:
        sentiment_weight: Optional sentiment weight override.
        bug_severity_weight: Optional bug severity weight override.

    Returns:
        PriorityScoringAgent instance.
    """
    global _priority_scoring_agent
    if _priority_scoring_agent is None or sentiment_weight is not None or bug_severity_weight is not None:
        _priority_scoring_agent = PriorityScoringAgent(
            sentiment_weight=sentiment_weight or 0.3,
            bug_severity_weight=bug_severity_weight or 0.5,
        )
    return _priority_scoring_agent


async def calculate_priority_node(state: BugBridgeState) -> BugBridgeState:
    """
    LangGraph node function for priority scoring.

    This function:
    1. Extracts feedback post and analysis results from state
    2. Runs priority scoring agent
    3. Updates state with priority score results

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with priority score results.
    """
    agent = get_priority_scoring_agent()
    return await agent.run(state)


__all__ = [
    "PriorityScoringAgent",
    "get_priority_scoring_agent",
    "calculate_priority_node",
    "calculate_engagement_score_from_post",
    "create_priority_scoring_prompt",
    "is_burning_issue",
    "PRIORITY_SCORING_SYSTEM_MESSAGE",
]

