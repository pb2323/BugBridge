"""
Ticket Assignment Utilities

Provides round-robin and component-based assignment logic for Jira tickets.
"""

from __future__ import annotations

import json
from typing import Dict, List, Literal, Optional

from bugbridge.config import get_settings
from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


AssignmentStrategy = Literal["none", "round_robin", "component_based", "priority_based"]


class AssignmentManager:
    """
    Manages ticket assignment based on configured strategy.

    Supports:
    - Round-robin: Cycles through a list of assignees
    - Component-based: Assigns based on component/team mapping
    - Priority-based: Assigns based on priority level mapping
    - None: No automatic assignment
    """

    def __init__(
        self,
        strategy: AssignmentStrategy = "none",
        round_robin_assignees: Optional[List[str]] = None,
        component_assignees: Optional[Dict[str, str]] = None,
        priority_assignees: Optional[Dict[str, str]] = None,
        state_file: Optional[str] = None,
    ):
        """
        Initialize assignment manager.

        Args:
            strategy: Assignment strategy to use.
            round_robin_assignees: List of assignee identifiers for round-robin.
            component_assignees: Dictionary mapping component names to assignees.
            priority_assignees: Dictionary mapping priority levels to assignees.
            state_file: Optional file path to persist round-robin state.
        """
        self.strategy = strategy
        self.round_robin_assignees = round_robin_assignees or []
        self.component_assignees = component_assignees or {}
        self.priority_assignees = priority_assignees or {}
        self.state_file = state_file or ".bugbridge_assignment_state.json"
        self._current_index = 0

        # Load round-robin state if available
        self._load_state()

    def _load_state(self) -> None:
        """Load round-robin state from file if it exists."""
        if not self.state_file:
            return

        try:
            with open(self.state_file, "r") as f:
                state = json.load(f)
                self._current_index = state.get("current_index", 0)
                logger.debug(f"Loaded assignment state: index={self._current_index}")
        except FileNotFoundError:
            logger.debug("Assignment state file not found, starting fresh")
        except Exception as e:
            logger.warning(f"Failed to load assignment state: {e}, starting fresh")

    def _save_state(self) -> None:
        """Save round-robin state to file."""
        if not self.state_file:
            return

        try:
            with open(self.state_file, "w") as f:
                json.dump({"current_index": self._current_index}, f)
        except Exception as e:
            logger.warning(f"Failed to save assignment state: {e}")

    def get_assignee(
        self,
        components: Optional[List[str]] = None,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Get assignee based on configured strategy.

        Args:
            components: List of component names (for component-based assignment).
            priority: Priority level (for priority-based assignment).
            labels: List of labels (can be used for component detection).

        Returns:
            Assignee identifier (account ID, email, or username) or None.
        """
        if self.strategy == "none":
            return None

        if self.strategy == "round_robin":
            return self._get_round_robin_assignee()

        if self.strategy == "component_based":
            return self._get_component_assignee(components or [], labels or [])

        if self.strategy == "priority_based":
            return self._get_priority_assignee(priority)

        logger.warning(f"Unknown assignment strategy: {self.strategy}")
        return None

    def _get_round_robin_assignee(self) -> Optional[str]:
        """
        Get next assignee using round-robin strategy.

        Returns:
            Next assignee in the round-robin list, or None if list is empty.
        """
        if not self.round_robin_assignees:
            logger.warning("Round-robin assignment requested but no assignees configured")
            return None

        # Get current assignee
        assignee = self.round_robin_assignees[self._current_index]

        # Advance index for next call
        self._current_index = (self._current_index + 1) % len(self.round_robin_assignees)

        # Save state
        self._save_state()

        logger.debug(f"Round-robin assignment: {assignee} (next index: {self._current_index})")
        return assignee

    def _get_component_assignee(self, components: List[str], labels: List[str]) -> Optional[str]:
        """
        Get assignee based on component mapping.

        Args:
            components: List of component names.
            labels: List of labels (may contain component hints).

        Returns:
            Assignee for the component, or None if no match.
        """
        # Check components first
        for component in components:
            if component in self.component_assignees:
                assignee = self.component_assignees[component]
                logger.debug(f"Component-based assignment: {component} -> {assignee}")
                return assignee

        # Check labels for component hints (e.g., "frontend", "backend", "api")
        for label in labels:
            # Try exact match
            if label in self.component_assignees:
                assignee = self.component_assignees[label]
                logger.debug(f"Component-based assignment (from label): {label} -> {assignee}")
                return assignee

            # Try partial match (e.g., "component-frontend" matches "frontend")
            for component_key, assignee in self.component_assignees.items():
                if component_key.lower() in label.lower() or label.lower() in component_key.lower():
                    logger.debug(f"Component-based assignment (partial match): {label} -> {assignee}")
                    return assignee

        logger.debug(f"Component-based assignment: No match found for components={components}, labels={labels}")
        return None

    def _get_priority_assignee(self, priority: Optional[str]) -> Optional[str]:
        """
        Get assignee based on priority mapping.

        Args:
            priority: Priority level (Critical, High, Medium, Low).

        Returns:
            Assignee for the priority level, or None if no match.
        """
        if not priority:
            logger.debug("Priority-based assignment: No priority provided")
            return None

        priority_normalized = priority.capitalize()
        if priority_normalized in self.priority_assignees:
            assignee = self.priority_assignees[priority_normalized]
            logger.debug(f"Priority-based assignment: {priority_normalized} -> {assignee}")
            return assignee

        logger.debug(f"Priority-based assignment: No match found for priority={priority}")
        return None


def get_assignment_manager() -> AssignmentManager:
    """
    Get assignment manager from configuration.

    Returns:
        Configured AssignmentManager instance.
    """
    try:
        settings = get_settings()
        jira_settings = settings.jira

        # Get assignment strategy from config
        strategy = getattr(jira_settings, "assignment_strategy", "none")
        round_robin_assignees = getattr(jira_settings, "round_robin_assignees", [])
        component_assignees = getattr(jira_settings, "component_assignees", {})
        priority_assignees = getattr(jira_settings, "priority_assignees", {})

        return AssignmentManager(
            strategy=strategy,
            round_robin_assignees=round_robin_assignees,
            component_assignees=component_assignees,
            priority_assignees=priority_assignees,
        )
    except Exception as e:
        logger.warning(f"Failed to load assignment configuration: {e}, using default (no assignment)")
        return AssignmentManager(strategy="none")


__all__ = [
    "AssignmentStrategy",
    "AssignmentManager",
    "get_assignment_manager",
]

