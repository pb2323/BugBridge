"""
Notification Agent

Generates contextual customer replies and posts them to Canny.io when Jira tickets are resolved.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from bugbridge.agents.base import BaseAgent
from bugbridge.config import CannySettings, get_settings
from bugbridge.integrations.canny import CannyClient, CannyAPIError
from bugbridge.integrations.xai import ChatXAI
from bugbridge.models.feedback import FeedbackPost
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


class CustomerReply(BaseModel):
    """
    Structured output for customer notification reply.

    Attributes:
        greeting: Opening greeting/thank you message
        resolution_confirmation: Confirmation that the issue has been resolved
        jira_ticket_link: Link to Jira ticket (if applicable)
        resolution_summary: Brief summary of what was fixed (optional)
        closing_message: Closing thank you message
        full_reply: Complete formatted reply message
    """

    greeting: str = Field(..., description="Opening greeting thanking the customer for their feedback", min_length=10)
    resolution_confirmation: str = Field(
        ..., description="Confirmation that the issue has been resolved", min_length=10
    )
    jira_ticket_link: Optional[str] = Field(
        None, description="Link to the Jira ticket if applicable (Markdown format)"
    )
    resolution_summary: Optional[str] = Field(
        None, description="Brief summary of what was fixed or resolved (optional)"
    )
    closing_message: str = Field(..., description="Closing thank you message", min_length=10)
    full_reply: str = Field(..., description="Complete formatted reply message in Markdown format", min_length=50)


def create_notification_prompt(
    feedback_post: FeedbackPost,
    jira_ticket_id: Optional[str],
    jira_ticket_url: Optional[str],
    resolution_status: str,
    resolution_summary: Optional[str] = None,
) -> str:
    """
    Create prompt template for generating customer notification reply.

    Args:
        feedback_post: Original feedback post from Canny.io.
        jira_ticket_id: Jira ticket key (e.g., "PROJ-123").
        jira_ticket_url: URL to the Jira ticket.
        resolution_status: Current Jira ticket status (e.g., "Done", "Resolved").
        resolution_summary: Optional summary of the resolution.

    Returns:
        Formatted prompt string for XAI LLM.
    """
    prompt_parts = [
        "You are a customer communication specialist. Generate a professional, contextual reply",
        "to notify a customer that their reported issue has been resolved.",
        "",
        "## Original Feedback",
        f"**Title:** {feedback_post.title}",
        f"**Content:** {feedback_post.content}",
        "",
        "## Resolution Information",
        f"**Status:** {resolution_status}",
    ]

    # Include URL for linking but not the ticket ID/key to avoid it appearing in the message
    if jira_ticket_url:
        prompt_parts.append(f"**Resolution Tracking URL:** {jira_ticket_url} (use this for linking, but do not show ticket ID in message)")

    if resolution_summary:
        prompt_parts.append(f"**Resolution Summary:** {resolution_summary}")

    prompt_parts.extend(
        [
            "",
            "## Requirements",
            "Generate a professional reply that:",
            "- Thanks the customer for their feedback",
            "- Confirms the issue has been resolved",
            "- Does NOT mention the Jira ticket ID or key (e.g., do not write 'Ticket ECS-48' or 'ECS-48')",
            "- Can include a generic link to view resolution details (optional, but do not show ticket ID in the link text)",
            "- Maintains a professional and friendly tone",
            "- Is concise but informative",
            "",
            "## Output Format",
            "You MUST respond with ONLY a JSON object with these fields:",
            "```json",
            "{",
            '  "greeting": "Opening greeting thanking the customer",',
            '  "resolution_confirmation": "Confirmation that issue is resolved",',
            '  "jira_ticket_link": "Markdown link without ticket ID (optional, use generic text like \"view the resolution\" or \"tracking system\")",',
            '  "resolution_summary": "Brief summary of fix (optional)",',
            '  "closing_message": "Closing thank you message",',
            '  "full_reply": "Complete formatted reply in Markdown"',
            "}",
            "```",
            "",
            "The full_reply field should contain the complete, formatted message that will",
            "be posted to Canny.io. Use Markdown formatting. Include:",
            "- A warm greeting thanking the customer",
            "- Clear confirmation of resolution",
            "- Optional generic link to view resolution (if available), but DO NOT include ticket ID/key in the link text",
            "  Example link format: [view the resolution]({ticket_url}) or [tracking system]({ticket_url})",
            "  DO NOT use formats like: [Ticket ECS-48](url) or [ECS-48](url)",
            "- Optional brief summary if resolution details are available",
            "- A closing thank you message",
            "",
            "IMPORTANT: Do not mention or display the Jira ticket ID or key anywhere in the message.",
            "",
            "Generate the JSON response now (no additional text, ONLY the JSON object):",
        ]
    )

    return "\n".join(prompt_parts)


def format_reply_message(reply: CustomerReply) -> str:
    """
    Format the structured reply into a final message.

    Args:
        reply: CustomerReply object with structured reply components.

    Returns:
        Formatted reply message in Markdown.
    """
    # Use the full_reply if provided, otherwise construct from components
    if reply.full_reply:
        return reply.full_reply.strip()

    # Construct reply from components
    parts = [reply.greeting]

    if reply.resolution_confirmation:
        parts.append("")
        parts.append(reply.resolution_confirmation)

    if reply.jira_ticket_link:
        parts.append("")
        parts.append(reply.jira_ticket_link)

    if reply.resolution_summary:
        parts.append("")
        parts.append(reply.resolution_summary)

    if reply.closing_message:
        parts.append("")
        parts.append(reply.closing_message)

    return "\n".join(parts).strip()


def determine_resolution_type(resolution_status: str) -> Literal["fixed", "wont_fix", "duplicate", "resolved"]:
    """
    Determine resolution type from status.

    Args:
        resolution_status: Jira ticket status.

    Returns:
        Resolution type category.
    """
    status_lower = resolution_status.lower()

    if "won't fix" in status_lower or "wont fix" in status_lower or "won't fix" in status_lower:
        return "wont_fix"
    elif "duplicate" in status_lower:
        return "duplicate"
    elif "fixed" in status_lower or "resolved" in status_lower or "done" in status_lower:
        return "fixed"
    else:
        return "resolved"


class NotificationAgent(BaseAgent):
    """
    Notification Agent for posting customer replies to Canny.io.

    This agent:
    - Generates contextual replies using XAI LLM
    - Formats replies with resolution confirmation and Jira ticket links
    - Posts comments to original Canny.io feedback posts
    - Prevents duplicate notifications
    - Tracks notification status and delivery
    """

    def __init__(
        self,
        llm: Optional[ChatXAI] = None,
        deterministic: bool = True,
        canny_client: Optional[CannyClient] = None,
    ):
        """
        Initialize Notification Agent.

        Args:
            llm: Optional XAI LLM instance (creates one if not provided).
            deterministic: Whether to enforce deterministic behavior.
            canny_client: Optional CannyClient instance (creates one if not provided).
        """
        super().__init__(
            name="notification_agent",
            llm=llm,
            deterministic=deterministic,
        )
        self._canny_client = canny_client
        self._settings: Optional[CannySettings] = None

    def _get_canny_client(self) -> CannyClient:
        """
        Get or create CannyClient instance.

        Returns:
            CannyClient instance.
        """
        if self._canny_client:
            return self._canny_client

        try:
            settings = get_settings()
            self._settings = settings.canny

            return CannyClient(
                api_key=self._settings.api_key.get_secret_value(),
                subdomain=self._settings.subdomain,
            )
        except Exception as e:
            logger.error(
                f"Failed to create Canny client: {str(e)}",
                extra={"agent_name": self.name},
                exc_info=True,
            )
            raise

    async def generate_reply(
        self,
        feedback_post: FeedbackPost,
        jira_ticket_id: Optional[str],
        jira_ticket_url: Optional[str],
        resolution_status: str,
        resolution_summary: Optional[str] = None,
    ) -> CustomerReply:
        """
        Generate customer notification reply using XAI LLM.

        Args:
            feedback_post: Original feedback post.
            jira_ticket_id: Jira ticket key.
            jira_ticket_url: URL to Jira ticket.
            resolution_status: Current resolution status.
            resolution_summary: Optional resolution summary.

        Returns:
            CustomerReply object with structured reply.
        """
        prompt = create_notification_prompt(
            feedback_post=feedback_post,
            jira_ticket_id=jira_ticket_id,
            jira_ticket_url=jira_ticket_url,
            resolution_status=resolution_status,
            resolution_summary=resolution_summary,
        )

        logger.info(
            f"Generating customer reply for post {feedback_post.post_id}",
            extra={
                "agent_name": self.name,
                "post_id": feedback_post.post_id,
                "ticket_id": jira_ticket_id,
                "resolution_status": resolution_status,
            },
        )

        # Generate structured reply using XAI LLM
        reply = await self.generate_structured_output(
            prompt=prompt,
            schema=CustomerReply,
            system_message="You are a professional customer communication specialist. You MUST respond with valid JSON only. Generate warm, helpful, and concise replies in JSON format.",
        )

        # Ensure full_reply is populated if not provided
        if not reply.full_reply:
            reply.full_reply = format_reply_message(reply)

        logger.info(
            f"Generated customer reply for post {feedback_post.post_id}",
            extra={
                "agent_name": self.name,
                "post_id": feedback_post.post_id,
                "reply_length": len(reply.full_reply),
            },
        )

        return reply

    async def check_duplicate_notification(self, post_id: str, state: BugBridgeState) -> bool:
        """
        Check if a notification has already been sent for this post.

        Args:
            post_id: Canny.io post ID.
            state: Current workflow state (to check metadata).

        Returns:
            True if notification already exists, False otherwise.

        Note:
            Checks state metadata first, then could check database in production.
            In production, would query: SELECT * FROM notifications WHERE feedback_post_id = post_id
        """
        # Check state metadata for existing notification
        metadata = state.get("metadata", {})
        notification_meta = metadata.get("notification")
        if notification_meta:
            # Check if notification was already posted
            if notification_meta.get("comment_id"):
                return True

        # TODO: Implement database check for existing notifications
        # from bugbridge.database.models import Notification
        # from bugbridge.database.session import get_session
        # async with get_session() as session:
        #     existing = await session.query(Notification).filter(
        #         Notification.feedback_post_id == post_id,
        #         Notification.notification_status == "sent"
        #     ).first()
        #     return existing is not None

        return False

    async def post_notification_comment(
        self,
        feedback_post: FeedbackPost,
        reply_message: str,
        author_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post notification comment to Canny.io feedback post.

        Args:
            feedback_post: Original feedback post.
            reply_message: Formatted reply message to post.
            author_id: Optional author ID (defaults to admin user from config).

        Returns:
            Comment response from Canny.io API.

        Raises:
            CannyAPIError: If comment posting fails.
        """
        canny_client = self._get_canny_client()

        # Get author_id from config if not provided
        if author_id is None:
            try:
                settings = get_settings()
                # Note: CANNY_ADMIN_USER_ID should be in settings
                # For now, we'll require it to be passed or raise
                raise ValueError("author_id must be provided")
            except Exception:
                raise ValueError("author_id must be provided if config is not available")

        logger.info(
            f"Posting notification comment to post {feedback_post.post_id}",
            extra={
                "agent_name": self.name,
                "post_id": feedback_post.post_id,
                "author_id": author_id,
                "reply_length": len(reply_message),
            },
        )

        try:
            response = await canny_client.post_comment(
                post_id=feedback_post.post_id,
                value=reply_message,
                author_id=author_id,
            )

            logger.info(
                f"Successfully posted notification comment to post {feedback_post.post_id}",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "comment_id": response.get("id"),
                },
            )

            return response

        except CannyAPIError as e:
            error_msg = f"Failed to post notification comment: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "status_code": e.status_code,
                },
                exc_info=True,
            )
            raise

    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """
        Execute notification posting to Canny.io.

        Args:
            state: Current workflow state containing feedback_post, jira_ticket_id, and jira_ticket_status.

        Returns:
            Updated workflow state with notification status.
        """
        # Validate required state
        feedback_post = state.get("feedback_post")
        if not feedback_post:
            error_msg = "Notification Agent requires feedback_post in state"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Ensure feedback_post is a FeedbackPost object
        if isinstance(feedback_post, dict):
            from bugbridge.models.feedback import FeedbackPost

            feedback_post = FeedbackPost.model_validate(feedback_post)

        # Check if ticket is resolved
        ticket_status = state.get("jira_ticket_status")
        if not ticket_status:
            error_msg = "Notification Agent requires jira_ticket_status in state"
            logger.error(error_msg, extra={"agent_name": self.name})
            return self.add_state_error(state, error_msg)

        # Get Jira ticket information
        jira_ticket_id = state.get("jira_ticket_id")
        jira_ticket_url = state.get("jira_ticket_url")

        # Check for duplicate notifications
        is_duplicate = await self.check_duplicate_notification(feedback_post.post_id, state)
        if is_duplicate:
            logger.warning(
                f"Notification already sent for post {feedback_post.post_id}, skipping",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                },
            )
            # Mark as notified but don't post again
            state["workflow_status"] = "notified"
            state = self.update_state_timestamp(state, "notified_at")
            return state

        # Determine resolution type
        resolution_type = determine_resolution_type(ticket_status)

        # Generate customer reply
        try:
            reply = await self.generate_reply(
                feedback_post=feedback_post,
                jira_ticket_id=jira_ticket_id,
                jira_ticket_url=jira_ticket_url,
                resolution_status=ticket_status,
                resolution_summary=None,  # Could be extracted from Jira ticket description in future
            )

            # Format reply message
            reply_message = format_reply_message(reply)

            # Post comment to Canny.io
            # Get author_id from config or state metadata
            try:
                settings = get_settings()
                author_id = settings.canny.admin_user_id
                if not author_id:
                    # Try to get from state metadata as fallback
                    author_id = state.get("metadata", {}).get("canny_admin_user_id")
                    if not author_id:
                        raise ValueError(
                            "Canny admin user ID not configured. Set CANNY__ADMIN_USER_ID in .env or provide in state metadata."
                        )
            except Exception as e:
                error_msg = f"Failed to get Canny admin user ID: {str(e)}"
                logger.error(error_msg, extra={"agent_name": self.name})
                return self.add_state_error(state, error_msg)

            comment_response = await self.post_notification_comment(
                feedback_post=feedback_post,
                reply_message=reply_message,
                author_id=author_id,
            )

            # Update workflow state
            state["workflow_status"] = "notified"
            state = self.update_state_timestamp(state, "notified_at")

            # Store notification metadata
            if "metadata" not in state:
                state["metadata"] = {}
            state["metadata"]["notification"] = {
                "comment_id": comment_response.get("id"),
                "posted_at": datetime.now(UTC).isoformat(),
                "reply_message": reply_message,
                "resolution_type": resolution_type,
                "ticket_id": jira_ticket_id,
            }

            # Log agent decision
            self.log_agent_decision(
                "notification_sent",
                f"Posted notification comment to post {feedback_post.post_id}",
                state,
                {
                    "post_id": feedback_post.post_id,
                    "ticket_id": jira_ticket_id,
                    "resolution_type": resolution_type,
                    "comment_id": comment_response.get("id"),
                },
            )

            # Log agent action
            self.log_agent_action(
                "notification_posted",
                {
                    "post_id": feedback_post.post_id,
                    "ticket_id": jira_ticket_id,
                    "comment_id": comment_response.get("id"),
                },
                state,
            )

            logger.info(
                f"Successfully notified customer for post {feedback_post.post_id}",
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "ticket_id": jira_ticket_id,
                },
            )

            return state

        except CannyAPIError as e:
            error_msg = f"Failed to post notification to Canny.io: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                    "status_code": e.status_code,
                },
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)

        except Exception as e:
            error_msg = f"Notification agent execution failed: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "agent_name": self.name,
                    "post_id": feedback_post.post_id,
                },
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)

    async def run(self, state: BugBridgeState) -> BugBridgeState:
        """
        Run the notification agent (wrapper for execute).

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state.
        """
        logger.info(
            "Starting notification agent execution",
            extra={"agent_name": self.name},
        )

        try:
            result_state = await self.execute(state)
            logger.info(
                "Notification agent execution completed",
                extra={"agent_name": self.name},
            )
            return result_state
        except Exception as e:
            error_msg = f"Notification agent execution failed: {str(e)}"
            logger.error(
                error_msg,
                extra={"agent_name": self.name},
                exc_info=True,
            )
            return self.add_state_error(state, error_msg)


async def notify_customer_node(state: BugBridgeState) -> BugBridgeState:
    """
    LangGraph node function for Notification Agent.

    Args:
        state: Current workflow state.

    Returns:
        Updated workflow state with notification status.
    """
    agent = NotificationAgent()
    return await agent.run(state)


def get_notification_agent() -> NotificationAgent:
    """
    Get or create Notification Agent instance.

    Returns:
        NotificationAgent instance.
    """
    return NotificationAgent()

