"""
Bug Detection Agent

Analyzes customer feedback to identify bugs vs feature requests using
XAI LLM with structured outputs for deterministic classification.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from bugbridge.agents.base import BaseAgent
from bugbridge.models.analysis import BugDetectionResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


# System message for bug detection specialist role
BUG_DETECTION_SYSTEM_MESSAGE = """You are a bug detection specialist with expertise in analyzing customer feedback 
to distinguish between bug reports and feature requests. Your analysis should be precise, thorough, and based on 
clear indicators such as:

- Keywords indicating bugs: "error", "broken", "not working", "crash", "bug", "issue", "fails", "problem"
- Error messages or crash reports
- Descriptions of unexpected behavior or functionality that doesn't work as intended
- Reports of things that previously worked but now don't
- Technical details suggesting system failures

For bug classifications, you must also assess severity:
- Critical: System crashes, data loss, security vulnerabilities, prevents core functionality
- High: Major functionality broken, affects many users, significant workarounds needed
- Medium: Moderate impact, some users affected, partial functionality
- Low: Minor issues, edge cases, cosmetic problems, minimal impact

Provide clear, structured analysis with confidence scores and reasoning."""


def create_bug_detection_prompt(feedback_post: FeedbackPost) -> str:
    """
    Create prompt for bug detection analysis.

    Args:
        feedback_post: Feedback post to analyze.

    Returns:
        Formatted prompt string.
    """
    prompt = f"""Analyze the following customer feedback and determine if it describes a bug or a feature request.

Feedback Post:
Title: {feedback_post.title}
Content: {feedback_post.content}

Post Metadata:
- Votes: {feedback_post.votes}
- Comments: {feedback_post.comments_count}
- Status: {feedback_post.status}
- Tags: {', '.join(feedback_post.tags) if feedback_post.tags else 'None'}
- Created: {feedback_post.created_at}

Provide a structured analysis with:
- is_bug: boolean indicating if this is a bug (True) or feature request (False)
- confidence: float (0-1) representing your confidence in the classification
- bug_severity: Critical|High|Medium|Low|N/A (severity if bug, N/A if feature request)
- keywords_identified: list[str] of keywords/phrases that indicate bug vs feature request
- reasoning: detailed explanation of your classification decision

Be thorough in your analysis. Consider:
1. Language used (error terminology, frustration indicators)
2. Whether functionality is described as broken vs missing
3. Context from tags and post metadata
4. Specificity of technical details (bugs tend to be more specific)
"""

    return prompt


class BugDetectionAgent(BaseAgent):
    """
    Agent for detecting bugs in customer feedback posts.

    Uses XAI LLM with structured outputs to classify feedback as bugs
    vs feature requests, providing confidence scores and severity ratings.
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        deterministic: bool = True,
    ):
        """
        Initialize Bug Detection Agent.

        Args:
            llm: Optional XAI LLM instance (creates one if not provided).
            deterministic: Whether to enforce deterministic behavior (temperature=0).
        """
        super().__init__(
            name="bug_detection_agent",
            llm=llm,
            deterministic=deterministic,
        )

    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """
        Execute bug detection analysis on feedback post.

        Args:
            state: Current workflow state containing feedback_post.

        Returns:
            Updated workflow state with bug_detection results.
        """
        # Validate that feedback post exists
        feedback_post = state.get("feedback_post")
        if not feedback_post:
            error_msg = "Bug Detection Agent requires feedback_post in state"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Ensure feedback_post is a FeedbackPost object
        if isinstance(feedback_post, dict):
            feedback_post = FeedbackPost.model_validate(feedback_post)

        logger.info(
            f"Starting bug detection analysis for post: {feedback_post.post_id}",
            extra={
                "agent_name": self.name,
                "post_id": feedback_post.post_id,
            },
        )

        try:
            # Create prompt
            prompt = create_bug_detection_prompt(feedback_post)

            # Log the decision to analyze
            self.log_agent_decision(
                decision="analyze_bug",
                reasoning=f"Analyzing feedback post {feedback_post.post_id} for bug classification",
                state=state,
            )

            # Generate structured output using XAI LLM
            result = await self.generate_structured_output(
                prompt=prompt,
                schema=BugDetectionResult,
                system_message=BUG_DETECTION_SYSTEM_MESSAGE,
            )

            # Ensure analyzed_at timestamp is set
            if not result.analyzed_at:
                result.analyzed_at = datetime.now(UTC)

            # Update state with bug detection results
            updated_state = {
                **state,
                "bug_detection": result,
                "workflow_status": "analyzed",
            }

            # Add timestamp
            updated_state = self.update_state_timestamp(updated_state, "bug_detected")

            # Log successful analysis
            self.log_agent_action(
                action="bug_detection_analysis",
                result="success",
                state=updated_state,
                context={
                    "is_bug": result.is_bug,
                    "confidence": result.confidence,
                    "severity": result.bug_severity,
                },
            )

            logger.info(
                f"Bug detection analysis completed: is_bug={result.is_bug}, "
                f"confidence={result.confidence}, severity={result.bug_severity}",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "is_bug": result.is_bug,
                    "confidence": result.confidence,
                    "severity": result.bug_severity,
                },
            )

            return updated_state

        except Exception as e:
            error_msg = f"Bug detection analysis failed: {str(e)}"
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
_bug_detection_agent: Optional[BugDetectionAgent] = None


def get_bug_detection_agent() -> BugDetectionAgent:
    """
    Get or create the global Bug Detection Agent instance.

    Returns:
        BugDetectionAgent instance.
    """
    global _bug_detection_agent
    if _bug_detection_agent is None:
        _bug_detection_agent = BugDetectionAgent()
    return _bug_detection_agent


async def analyze_bug_node(state: BugBridgeState) -> BugBridgeState:
    """
    LangGraph node function for bug detection analysis.

    This function:
    1. Extracts feedback post from state
    2. Runs bug detection agent
    3. Updates state with analysis results

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with bug detection results.
    """
    agent = get_bug_detection_agent()
    return await agent.run(state)


__all__ = [
    "BugDetectionAgent",
    "get_bug_detection_agent",
    "analyze_bug_node",
    "create_bug_detection_prompt",
    "BUG_DETECTION_SYSTEM_MESSAGE",
]

