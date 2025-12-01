"""
BugBridge API Package

FastAPI application for the BugBridge dashboard backend.
"""

from bugbridge.api.main import create_app, get_app

__all__ = [
    "create_app",
    "get_app",
]

