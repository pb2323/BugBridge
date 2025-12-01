"""
Sentiment Analysis Agent

Analyzes emotional tone and urgency of customer feedback using
XAI LLM with structured outputs for deterministic sentiment classification.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from bugbridge.agents.base import BaseAgent
from bugbridge.models.analysis import SentimentAnalysisResult
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


# System message for sentiment analysis specialist role
SENTIMENT_ANALYSIS_SYSTEM_MESSAGE = """You are a sentiment analysis specialist with expertise in analyzing emotional 
tone, urgency, and sentiment of customer feedback. Your analysis should be nuanced, contextual, and consider:

- Emotional indicators: Language expressing frustration, anger, satisfaction, disappointment, excitement
- Urgency signals: Words like "urgent", "critical", "ASAP", "blocking", "immediately", or phrases indicating time sensitivity
- Tone markers: Punctuation (multiple exclamation marks, question marks), capitalization (ALL CAPS), emotive language
- Context clues: Historical context (recurring issues), relationship with product, expectations vs. reality
- Mixed emotions: Ability to detect complex emotional states (e.g., "frustrated but hopeful", "excited but concerned")

Sentiment classifications:
- Positive: Expresses satisfaction, appreciation, excitement, or constructive feedback
- Neutral: Factual, objective, balanced tone without strong emotional indicators
- Negative: Expresses dissatisfaction, disappointment, or concerns without strong frustration
- Frustrated: Shows irritation, impatience, or repeated issues causing annoyance
- Angry: Strong negative emotions, hostility, or extreme dissatisfaction

Urgency levels:
- High: Immediate action needed, blocking issues, critical problems, time-sensitive requests
- Medium: Important but not blocking, should be addressed soon, moderate time sensitivity
- Low: No immediate time pressure, can be addressed in normal course of business

Provide clear, structured analysis with normalized sentiment scores and detailed reasoning."""


def create_sentiment_analysis_prompt(feedback_post: FeedbackPost) -> str:
    """
    Create prompt for sentiment analysis.

    Args:
        feedback_post: Feedback post to analyze.

    Returns:
        Formatted prompt string.
    """
    prompt = f"""Analyze the emotional tone and urgency of the following customer feedback.

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
- sentiment: Positive|Neutral|Negative|Frustrated|Angry (overall sentiment classification)
- sentiment_score: float (0-1, where 0 is very negative, 1 is very positive)
- urgency: High|Medium|Low (urgency level detected in the language)
- emotions_detected: list[str] of specific emotions identified (e.g., 'frustrated', 'hopeful', 'disappointed', 'excited')
- reasoning: detailed explanation of your sentiment analysis

Be thorough in your analysis. Consider:
1. Language used (emotional words, intensity indicators)
2. Punctuation and capitalization patterns
3. Context from tags and engagement metrics
4. Urgency indicators in the text
5. Mixed or complex emotional states
6. Relationship between sentiment and the issue being described

Pay attention to subtle cues:
- Repeated words or phrases indicating emphasis
- Comparison language ("used to work", "worse than before")
- Conditional statements that affect urgency
- Questions that might indicate confusion or concern
"""

    return prompt


class SentimentAnalysisAgent(BaseAgent):
    """
    Agent for analyzing sentiment and urgency in customer feedback posts.

    Uses XAI LLM with structured outputs to classify sentiment, detect emotions,
    and assess urgency levels in feedback content.
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        deterministic: bool = True,
    ):
        """
        Initialize Sentiment Analysis Agent.

        Args:
            llm: Optional XAI LLM instance (creates one if not provided).
            deterministic: Whether to enforce deterministic behavior (temperature=0).
        """
        super().__init__(
            name="sentiment_analysis_agent",
            llm=llm,
            deterministic=deterministic,
        )

    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """
        Execute sentiment analysis on feedback post.

        Args:
            state: Current workflow state containing feedback_post.

        Returns:
            Updated workflow state with sentiment_analysis results.
        """
        # Validate that feedback post exists
        feedback_post = state.get("feedback_post")
        if not feedback_post:
            error_msg = "Sentiment Analysis Agent requires feedback_post in state"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Ensure feedback_post is a FeedbackPost object
        if isinstance(feedback_post, dict):
            feedback_post = FeedbackPost.model_validate(feedback_post)

        logger.info(
            f"Starting sentiment analysis for post: {feedback_post.post_id}",
            extra={
                "agent_name": self.name,
                "post_id": feedback_post.post_id,
            },
        )

        try:
            # Create prompt
            prompt = create_sentiment_analysis_prompt(feedback_post)

            # Log the decision to analyze
            self.log_agent_decision(
                decision="analyze_sentiment",
                reasoning=f"Analyzing feedback post {feedback_post.post_id} for sentiment and urgency",
                state=state,
            )

            # Generate structured output using XAI LLM
            result = await self.generate_structured_output(
                prompt=prompt,
                schema=SentimentAnalysisResult,
                system_message=SENTIMENT_ANALYSIS_SYSTEM_MESSAGE,
            )

            # Ensure analyzed_at timestamp is set
            if not result.analyzed_at:
                result.analyzed_at = datetime.now(UTC)

            # Update state with sentiment analysis results
            updated_state = {
                **state,
                "sentiment_analysis": result,
            }

            # Update workflow status if not already set
            if not updated_state.get("workflow_status"):
                updated_state["workflow_status"] = "analyzed"

            # Add timestamp
            updated_state = self.update_state_timestamp(updated_state, "sentiment_analyzed")

            # Log successful analysis
            self.log_agent_action(
                action="sentiment_analysis",
                result="success",
                state=updated_state,
                context={
                    "sentiment": result.sentiment,
                    "sentiment_score": result.sentiment_score,
                    "urgency": result.urgency,
                    "emotions_count": len(result.emotions_detected),
                },
            )

            logger.info(
                f"Sentiment analysis completed: sentiment={result.sentiment}, "
                f"score={result.sentiment_score}, urgency={result.urgency}",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "sentiment": result.sentiment,
                    "sentiment_score": result.sentiment_score,
                    "urgency": result.urgency,
                },
            )

            return updated_state

        except Exception as e:
            error_msg = f"Sentiment analysis failed: {str(e)}"
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
_sentiment_analysis_agent: Optional[SentimentAnalysisAgent] = None


def get_sentiment_analysis_agent() -> SentimentAnalysisAgent:
    """
    Get or create the global Sentiment Analysis Agent instance.

    Returns:
        SentimentAnalysisAgent instance.
    """
    global _sentiment_analysis_agent
    if _sentiment_analysis_agent is None:
        _sentiment_analysis_agent = SentimentAnalysisAgent()
    return _sentiment_analysis_agent


async def analyze_sentiment_node(state: BugBridgeState) -> BugBridgeState:
    """
    LangGraph node function for sentiment analysis.

    This function:
    1. Extracts feedback post from state
    2. Runs sentiment analysis agent
    3. Updates state with analysis results

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with sentiment analysis results.
    """
    agent = get_sentiment_analysis_agent()
    return await agent.run(state)


__all__ = [
    "SentimentAnalysisAgent",
    "get_sentiment_analysis_agent",
    "analyze_sentiment_node",
    "create_sentiment_analysis_prompt",
    "SENTIMENT_ANALYSIS_SYSTEM_MESSAGE",
]

