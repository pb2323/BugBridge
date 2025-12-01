"""
File Storage Service

Handles saving reports to filesystem or cloud storage.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


class FileStorageError(Exception):
    """Raised when file storage operations fail."""

    pass


class FileStorageService:
    """
    File storage service for saving reports to filesystem.

    Supports saving reports as Markdown files with organized directory structure.
    """

    def __init__(
        self,
        base_path: str = "./reports",
        create_dirs: bool = True,
    ):
        """
        Initialize file storage service.

        Args:
            base_path: Base directory path for storing reports.
            create_dirs: Whether to create directories if they don't exist.
        """
        self.base_path = Path(base_path)
        self.create_dirs = create_dirs

        if self.create_dirs:
            self.base_path.mkdir(parents=True, exist_ok=True)

    def save_report(
        self,
        report_content: str,
        report_date: datetime,
        report_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save report to filesystem.

        Args:
            report_content: Markdown report content.
            report_date: Report date.
            report_id: Optional report ID for filename.
            metadata: Optional metadata to save as JSON.

        Returns:
            Path to saved report file.

        Raises:
            FileStorageError: If file saving fails.
        """
        try:
            # Create date-based directory structure: reports/YYYY/MM/
            year = report_date.year
            month = report_date.month
            date_dir = self.base_path / str(year) / f"{month:02d}"

            if self.create_dirs:
                date_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename
            date_str = report_date.strftime("%Y-%m-%d")
            if report_id:
                filename = f"report_{date_str}_{report_id[:8]}.md"
            else:
                filename = f"report_{date_str}.md"

            file_path = date_dir / filename

            # Save report content
            file_path.write_text(report_content, encoding="utf-8")

            logger.info(
                f"Saved report to {file_path}",
                extra={
                    "file_path": str(file_path),
                    "report_date": date_str,
                    "report_id": report_id,
                },
            )

            # Save metadata if provided
            if metadata:
                metadata_path = file_path.with_suffix(".json")
                metadata_path.write_text(
                    json.dumps(metadata, indent=2, default=str),
                    encoding="utf-8",
                )
                logger.debug(f"Saved report metadata to {metadata_path}")

            return str(file_path)

        except Exception as e:
            error_msg = f"Failed to save report to filesystem: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "report_date": report_date.isoformat(),
                    "report_id": report_id,
                },
                exc_info=True,
            )
            raise FileStorageError(error_msg) from e

    def get_report_path(
        self,
        report_date: datetime,
        report_id: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Get path to report file if it exists.

        Args:
            report_date: Report date.
            report_id: Optional report ID.

        Returns:
            Path to report file if exists, None otherwise.
        """
        year = report_date.year
        month = report_date.month
        date_dir = self.base_path / str(year) / f"{month:02d}"

        date_str = report_date.strftime("%Y-%m-%d")
        if report_id:
            filename = f"report_{date_str}_{report_id[:8]}.md"
        else:
            filename = f"report_{date_str}.md"

        file_path = date_dir / filename

        if file_path.exists():
            return file_path

        return None


__all__ = [
    "FileStorageService",
    "FileStorageError",
]

