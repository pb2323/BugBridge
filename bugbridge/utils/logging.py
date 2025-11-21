"""
Structured logging configuration for BugBridge.

This module provides structured logging capabilities for the entire platform,
including audit logging for agent decisions and comprehensive error logging
with context for debugging.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from bugbridge.config import get_settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs for easier parsing
    and integration with log aggregation systems.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields passed via logger's extra parameter
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        # Add workflow context if present
        if hasattr(record, "workflow_id"):
            log_data["workflow_id"] = record.workflow_id

        if hasattr(record, "agent_name"):
            log_data["agent_name"] = record.agent_name

        if hasattr(record, "post_id"):
            log_data["post_id"] = record.post_id

        if hasattr(record, "jira_ticket_id"):
            log_data["jira_ticket_id"] = record.jira_ticket_id

        # Add duration if present (for performance tracking)
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        return json.dumps(log_data, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for local development and debugging.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format."""
        timestamp = datetime.fromtimestamp(record.created).isoformat()
        level = record.levelname.ljust(8)
        logger = record.name

        base_msg = f"[{timestamp}] {level} {logger} - {record.getMessage()}"

        # Add context fields
        context_parts = []
        if hasattr(record, "workflow_id"):
            context_parts.append(f"workflow={record.workflow_id}")

        if hasattr(record, "agent_name"):
            context_parts.append(f"agent={record.agent_name}")

        if hasattr(record, "post_id"):
            context_parts.append(f"post_id={record.post_id}")

        if hasattr(record, "jira_ticket_id"):
            context_parts.append(f"jira={record.jira_ticket_id}")

        if hasattr(record, "duration_ms"):
            context_parts.append(f"duration={record.duration_ms}ms")

        if context_parts:
            base_msg += f" | {' '.join(context_parts)}"

        # Add exception if present
        if record.exc_info:
            base_msg += f"\n{self.formatException(record.exc_info)}"

        return base_msg


def setup_logging(
    level: Optional[str] = None,
    structured: Optional[bool] = None,
    stream: Optional[Any] = None,
) -> logging.Logger:
    """
    Configure and return the root BugBridge logger.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               If None, uses level from settings.
        structured: Whether to use JSON structured logging.
                   If None, uses structured logging in non-local environments.
        stream: Output stream (defaults to sys.stderr).

    Returns:
        Configured root logger for BugBridge.
    """
    # Try to get settings, but use defaults if not configured yet
    try:
        settings = get_settings()
        default_level = settings.log_level
        default_structured = settings.environment != "local" or settings.debug
    except Exception:
        # Settings not configured yet, use safe defaults
        default_level = "INFO"
        default_structured = False

    # Determine logging level
    log_level = level if level else default_level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Determine formatter based on environment
    if structured is None:
        structured = default_structured

    # Set up root logger
    root_logger = logging.getLogger("bugbridge")
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create handler
    if stream is None:
        stream = sys.stderr

    handler = logging.StreamHandler(stream)
    handler.setLevel(numeric_level)

    # Set formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Prevent propagation to root logger to avoid duplicate logs
    root_logger.propagate = False

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module or component.

    Args:
        name: Logger name (typically __name__ of the calling module).

    Returns:
        Logger instance configured for BugBridge.
    """
    # Ensure root logger is set up
    root_logger = logging.getLogger("bugbridge")
    if not root_logger.handlers:
        setup_logging()

    # Return child logger
    return logging.getLogger(f"bugbridge.{name}")


class AuditLogger:
    """
    Specialized logger for audit trails of agent decisions and actions.

    This logger automatically includes structured fields for audit purposes.
    """

    def __init__(self, logger: logging.Logger):
        """Initialize audit logger with a base logger."""
        self.logger = logger

    def log_agent_decision(
        self,
        agent_name: str,
        decision: str,
        reasoning: str,
        workflow_id: Optional[str] = None,
        post_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an agent decision for audit purposes.

        Args:
            agent_name: Name of the agent making the decision.
            decision: The decision made by the agent.
            reasoning: Explanation of why the decision was made.
            workflow_id: Optional workflow identifier.
            post_id: Optional feedback post identifier.
            context: Optional additional context fields.
        """
        extra = {
            "agent_name": agent_name,
            "workflow_id": workflow_id,
            "post_id": post_id,
            "extra_fields": {
                "event_type": "agent_decision",
                "decision": decision,
                "reasoning": reasoning,
                **(context or {}),
            },
        }
        self.logger.info(f"Agent decision: {agent_name} - {decision}", extra=extra)

    def log_agent_action(
        self,
        agent_name: str,
        action: str,
        result: str,
        workflow_id: Optional[str] = None,
        post_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log an agent action for audit purposes.

        Args:
            agent_name: Name of the agent performing the action.
            action: Description of the action performed.
            result: Result of the action (e.g., "success", "failure").
            workflow_id: Optional workflow identifier.
            post_id: Optional feedback post identifier.
            duration_ms: Optional duration in milliseconds.
            context: Optional additional context fields.
        """
        extra: Dict[str, Any] = {
            "agent_name": agent_name,
            "workflow_id": workflow_id,
            "post_id": post_id,
            "extra_fields": {
                "event_type": "agent_action",
                "action": action,
                "result": result,
                **(context or {}),
            },
        }

        if duration_ms is not None:
            extra["duration_ms"] = duration_ms

        level = logging.INFO if result == "success" else logging.WARNING
        self.logger.log(
            level,
            f"Agent action: {agent_name} - {action} - {result}",
            extra=extra,
        )

    def log_workflow_state_change(
        self,
        workflow_id: str,
        from_state: str,
        to_state: str,
        post_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a workflow state transition.

        Args:
            workflow_id: Workflow identifier.
            from_state: Previous workflow state.
            to_state: New workflow state.
            post_id: Optional feedback post identifier.
            context: Optional additional context fields.
        """
        extra = {
            "workflow_id": workflow_id,
            "post_id": post_id,
            "extra_fields": {
                "event_type": "workflow_state_change",
                "from_state": from_state,
                "to_state": to_state,
                **(context or {}),
            },
        }
        self.logger.info(
            f"Workflow state change: {from_state} -> {to_state}",
            extra=extra,
        )


def get_audit_logger(name: str = "audit") -> AuditLogger:
    """
    Get an audit logger instance for tracking agent decisions and actions.

    Args:
        name: Logger name for audit logs.

    Returns:
        AuditLogger instance.
    """
    logger = get_logger(name)
    return AuditLogger(logger)


__all__ = [
    "setup_logging",
    "get_logger",
    "AuditLogger",
    "get_audit_logger",
    "StructuredFormatter",
    "HumanReadableFormatter",
]

