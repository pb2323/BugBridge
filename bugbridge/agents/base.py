"""
Base Agent Class

Provides common functionality for all AI agents including logging,
error handling, state management, and structured output support.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Dict, Optional, Type

from pydantic import BaseModel

from bugbridge.integrations.xai import ChatXAI, get_xai_llm
from bugbridge.models.state import BugBridgeState
from bugbridge.utils.logging import get_audit_logger, get_logger

logger = get_logger(__name__)
audit_logger = get_audit_logger()


class BaseAgent(ABC):
    """
    Base class for all BugBridge AI agents.

    Provides common functionality:
    - Logging with structured audit trails
    - Error handling with retry logic
    - State management helpers
    - Structured output support via XAI LLM
    - Agent decision tracking
    """

    def __init__(
        self,
        name: str,
        llm: Optional[ChatXAI] = None,
        deterministic: bool = True,
    ):
        """
        Initialize base agent.

        Args:
            name: Agent name for logging and identification.
            llm: Optional XAI LLM instance (creates one if not provided).
            deterministic: Whether to enforce deterministic behavior (temperature=0).
        """
        self.name = name
        self.llm = llm or get_xai_llm()
        self.deterministic = deterministic

        # Ensure deterministic behavior if requested
        if self.deterministic:
            self.llm.temperature = 0.0

        logger.info(
            f"Initialized agent: {self.name}",
            extra={
                "agent_name": self.name,
                "deterministic": self.deterministic,
                "model": self.llm.model,
            },
        )

    def log_agent_decision(
        self,
        decision: str,
        reasoning: str,
        state: Optional[BugBridgeState] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an agent decision for audit purposes.

        Args:
            decision: The decision made by the agent.
            reasoning: Explanation of why the decision was made.
            state: Optional workflow state.
            context: Optional additional context fields.
        """
        workflow_id = None
        post_id = None

        if state and state.get("feedback_post"):
            feedback_post = state["feedback_post"]
            if hasattr(feedback_post, "post_id"):
                post_id = feedback_post.post_id
                workflow_id = post_id
            elif isinstance(feedback_post, dict):
                post_id = feedback_post.get("post_id")
                workflow_id = post_id

        audit_logger.log_agent_decision(
            agent_name=self.name,
            decision=decision,
            reasoning=reasoning,
            workflow_id=workflow_id,
            post_id=post_id,
            context=context or {},
        )

    def log_agent_action(
        self,
        action: str,
        result: str,
        state: Optional[BugBridgeState] = None,
        duration_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an agent action for audit purposes.

        Args:
            action: Description of the action performed.
            result: Result of the action (e.g., "success", "failure").
            state: Optional workflow state.
            duration_ms: Optional duration in milliseconds.
            context: Optional additional context fields.
        """
        workflow_id = None
        post_id = None

        if state and state.get("feedback_post"):
            feedback_post = state["feedback_post"]
            if hasattr(feedback_post, "post_id"):
                post_id = feedback_post.post_id
            elif isinstance(feedback_post, dict):
                post_id = feedback_post.get("post_id")

        audit_logger.log_agent_action(
            agent_name=self.name,
            action=action,
            result=result,
            workflow_id=workflow_id,
            post_id=post_id,
            duration_ms=duration_ms,
            context=context or {},
        )

    async def generate_structured_output(
        self,
        prompt: str,
        schema: Type[BaseModel],
        system_message: Optional[str] = None,
        **kwargs: Any,
    ) -> BaseModel:
        """
        Generate structured output using XAI LLM with Pydantic schema.

        Args:
            prompt: User prompt/instruction.
            schema: Pydantic model class for structured output.
            system_message: Optional system message for the LLM.
            **kwargs: Additional parameters for LLM generation.

        Returns:
            Parsed Pydantic model instance.

        Raises:
            ValueError: If output cannot be parsed into schema.
        """
        from langchain_core.messages import HumanMessage, SystemMessage

        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        try:
            logger.debug(
                f"Generating structured output for {self.name}",
                extra={
                    "agent_name": self.name,
                    "schema": schema.__name__,
                },
            )

            # Use structured output helper from LLM
            structured_llm = self.llm.with_structured_output(schema, **kwargs)
            result = await structured_llm.ainvoke(messages)

            logger.debug(
                f"Successfully generated structured output for {self.name}",
                extra={
                    "agent_name": self.name,
                    "schema": schema.__name__,
                },
            )

            return result

        except Exception as e:
            logger.error(
                f"Failed to generate structured output for {self.name}: {str(e)}",
                extra={
                    "agent_name": self.name,
                    "schema": schema.__name__,
                },
                exc_info=True,
            )
            raise

    def update_state_timestamp(
        self,
        state: BugBridgeState,
        stage: str,
    ) -> BugBridgeState:
        """
        Update workflow state with a timestamp for the current stage.

        Args:
            state: Current workflow state.
            stage: Stage name (e.g., "analyzed", "ticket_created").

        Returns:
            Updated state with new timestamp.
        """
        timestamps = state.get("timestamps", {}).copy()
        timestamps[stage] = datetime.now(UTC)

        return {
            **state,
            "timestamps": timestamps,
        }

    def add_state_error(
        self,
        state: BugBridgeState,
        error_message: str,
    ) -> BugBridgeState:
        """
        Add an error message to workflow state.

        Args:
            state: Current workflow state.
            error_message: Error message to add.

        Returns:
            Updated state with error added.
        """
        errors = state.get("errors", []).copy()
        errors.append(error_message)

        return {
            **state,
            "errors": errors,
        }

    def update_state_metadata(
        self,
        state: BugBridgeState,
        key: str,
        value: Any,
    ) -> BugBridgeState:
        """
        Update workflow state metadata.

        Args:
            state: Current workflow state.
            key: Metadata key.
            value: Metadata value.

        Returns:
            Updated state with metadata updated.
        """
        metadata = state.get("metadata", {}).copy()
        metadata[key] = value

        return {
            **state,
            "metadata": metadata,
        }

    @abstractmethod
    async def execute(self, state: BugBridgeState) -> BugBridgeState:
        """
        Execute the agent's main logic.

        This method must be implemented by all concrete agent classes.

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state.
        """
        pass

    async def run(
        self,
        state: BugBridgeState,
    ) -> BugBridgeState:
        """
        Run the agent with error handling and logging.

        This is the main entry point for executing agents. It wraps
        the execute() method with error handling and audit logging.

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state.
        """
        start_time = datetime.now(UTC)

        try:
            logger.info(
                f"Starting agent execution: {self.name}",
                extra={
                    "agent_name": self.name,
                    "workflow_status": state.get("workflow_status"),
                },
            )

            # Execute agent logic
            updated_state = await self.execute(state)

            # Calculate duration
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Log successful execution
            self.log_agent_action(
                action=f"execute_{self.name}",
                result="success",
                state=updated_state,
                duration_ms=duration_ms,
            )

            logger.info(
                f"Agent execution completed: {self.name}",
                extra={
                    "agent_name": self.name,
                    "duration_ms": duration_ms,
                    "workflow_status": updated_state.get("workflow_status"),
                },
            )

            return updated_state

        except Exception as e:
            # Calculate duration
            duration_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000

            # Log failed execution
            error_message = f"Agent {self.name} failed: {str(e)}"
            self.log_agent_action(
                action=f"execute_{self.name}",
                result="failure",
                state=state,
                duration_ms=duration_ms,
                context={"error": str(e)},
            )

            logger.error(
                error_message,
                extra={
                    "agent_name": self.name,
                    "duration_ms": duration_ms,
                },
                exc_info=True,
            )

            # Update state with error
            return self.add_state_error(
                {
                    **state,
                    "workflow_status": "failed",
                },
                error_message,
            )


__all__ = [
    "BaseAgent",
]

