"""Configuration management for BugBridge platform"""

import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class CannyConfig(BaseSettings):
    """Canny.io API configuration"""
    
    api_key: str = Field(..., validation_alias="CANNY_API_KEY")
    subdomain: str = Field(..., validation_alias="CANNY_SUBDOMAIN")
    board_id: str = Field(..., validation_alias="CANNY_BOARD_ID")
    admin_user_id: str = Field(..., validation_alias="CANNY_ADMIN_USER_ID")
    sync_interval: int = Field(default=3600, validation_alias="CANNY_SYNC_INTERVAL")
    
    @property
    def base_url(self) -> str:
        return "https://canny.io/api/v1"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class JiraMCPConfig(BaseSettings):
    """Jira MCP server configuration"""
    
    server_url: str = Field(default="http://localhost:8000", validation_alias="JIRA_MCP_SERVER_URL")
    project_key: str = Field(..., validation_alias="JIRA_PROJECT_KEY")
    resolution_statuses: str = Field(default="Done,Resolved,Fixed", validation_alias="JIRA_RESOLUTION_STATUSES")
    
    @property
    def resolution_status_list(self) -> List[str]:
        return [s.strip() for s in self.resolution_statuses.split(",")]
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class XAIConfig(BaseSettings):
    """XAI API configuration"""
    
    api_key: str = Field(..., validation_alias="XAI_API_KEY")
    model: str = Field(default="grok-beta", validation_alias="XAI_MODEL")
    temperature: float = Field(default=0.0, validation_alias="XAI_TEMPERATURE")
    
    @property
    def base_url(self) -> str:
        return "https://api.x.ai/v1"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class DatabaseConfig(BaseSettings):
    """Database configuration"""
    
    url: str = Field(default="sqlite+aiosqlite:///./bugbridge.db", validation_alias="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class ReportingConfig(BaseSettings):
    """Reporting configuration"""
    
    schedule: str = Field(default="0 9 * * *", validation_alias="REPORT_SCHEDULE")
    recipients: str = Field(default="team@bugbridge.com", validation_alias="REPORT_RECIPIENTS")
    
    @property
    def recipient_list(self) -> List[str]:
        return [r.strip() for r in self.recipients.split(",")]
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class AgentConfig(BaseSettings):
    """Agent configuration"""
    
    retry_max_attempts: int = Field(default=3, validation_alias="AGENT_RETRY_MAX_ATTEMPTS")
    retry_backoff: float = Field(default=2.0, validation_alias="AGENT_RETRY_BACKOFF")
    timeout: int = Field(default=300, validation_alias="AGENT_TIMEOUT")
    
    class Config:
        env_file = ".env"
        extra = "ignore"


class Config:
    """Main configuration class aggregating all configs"""
    
    def __init__(self):
        self.canny = CannyConfig()
        self.jira = JiraMCPConfig()
        self.xai = XAIConfig()
        self.database = DatabaseConfig()
        self.reporting = ReportingConfig()
        self.agent = AgentConfig()
    
    def validate(self) -> bool:
        """Validate all configuration settings"""
        try:
            # Validate required API keys
            assert self.canny.api_key, "CANNY_API_KEY is required"
            assert self.xai.api_key, "XAI_API_KEY is required"
            assert self.jira.project_key, "JIRA_PROJECT_KEY is required"
            return True
        except AssertionError as e:
            print(f"Configuration validation failed: {e}")
            return False


# Global config instance
config = Config()
