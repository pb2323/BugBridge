"""
API Routes Package

FastAPI route handlers for the BugBridge API.
"""

from bugbridge.api.routes.auth import router as auth_router
from bugbridge.api.routes.config import router as config_router
from bugbridge.api.routes.feedback import router as feedback_router
from bugbridge.api.routes.jira_tickets import router as jira_tickets_router
from bugbridge.api.routes.metrics import router as metrics_router
from bugbridge.api.routes.reports import router as reports_router

__all__ = [
    "auth_router",
    "config_router",
    "feedback_router",
    "jira_tickets_router",
    "metrics_router",
    "reports_router",
]

