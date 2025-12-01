"""
Email Delivery Service

Handles sending reports and notifications via email using SMTP.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from bugbridge.utils.logging import get_logger

logger = get_logger(__name__)


class EmailDeliveryError(Exception):
    """Raised when email delivery fails."""

    pass


class EmailService:
    """
    Email delivery service for sending reports and notifications.

    Supports SMTP-based email delivery with configurable settings.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        use_tls: bool = True,
        from_email: Optional[str] = None,
    ):
        """
        Initialize email service.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port (default: 587 for TLS).
            smtp_username: SMTP username for authentication.
            smtp_password: SMTP password for authentication.
            use_tls: Whether to use TLS encryption (default: True).
            from_email: Default sender email address.
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.from_email = from_email or smtp_username

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        body_type: str = "plain",
        from_email: Optional[str] = None,
    ) -> None:
        """
        Send email via SMTP.

        Args:
            to_emails: List of recipient email addresses.
            body_type: Email body type ('plain' or 'html').
            subject: Email subject line.
            body: Email body content.
            from_email: Sender email address (defaults to configured from_email).

        Raises:
            EmailDeliveryError: If email sending fails.
        """
        if not to_emails:
            raise ValueError("At least one recipient email address is required")

        from_addr = from_email or self.from_email
        if not from_addr:
            raise ValueError("Sender email address must be provided")

        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = from_addr
        msg["To"] = ", ".join(to_emails)
        msg["Subject"] = subject

        # Add body
        msg.attach(MIMEText(body, body_type))

        try:
            logger.info(
                f"Sending email to {len(to_emails)} recipient(s)",
                extra={
                    "to_emails": to_emails,
                    "subject": subject,
                    "from_email": from_addr,
                },
            )

            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.set_debuglevel(0)  # Set to 1 for debug output

            if self.use_tls:
                server.starttls()

            # Authenticate if credentials provided
            if self.smtp_username and self.smtp_password:
                server.login(self.smtp_username, self.smtp_password)

            # Send email
            server.sendmail(from_addr, to_emails, msg.as_string())
            server.quit()

            logger.info(
                f"Successfully sent email to {len(to_emails)} recipient(s)",
                extra={
                    "to_emails": to_emails,
                    "subject": subject,
                },
            )

        except smtplib.SMTPException as e:
            error_msg = f"SMTP error sending email: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "to_emails": to_emails,
                    "subject": subject,
                },
                exc_info=True,
            )
            raise EmailDeliveryError(error_msg) from e

        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "to_emails": to_emails,
                    "subject": subject,
                },
                exc_info=True,
            )
            raise EmailDeliveryError(error_msg) from e

    def send_report_email(
        self,
        to_emails: List[str],
        report_content: str,
        report_date: str,
        from_email: Optional[str] = None,
    ) -> None:
        """
        Send daily report via email.

        Args:
            to_emails: List of recipient email addresses.
            report_content: Markdown report content.
            report_date: Report date string.
            from_email: Sender email address (optional).

        Raises:
            EmailDeliveryError: If email sending fails.
        """
        subject = f"BugBridge Daily Report - {report_date}"

        # Convert Markdown to HTML for better email formatting
        # For now, send as plain text with Markdown
        # In production, could use markdown library to convert to HTML
        body = f"""BugBridge Daily Summary Report

{report_content}

---
This is an automated report from BugBridge.
"""

        self.send_email(
            to_emails=to_emails,
            subject=subject,
            body=body,
            body_type="plain",
            from_email=from_email,
        )


__all__ = [
    "EmailService",
    "EmailDeliveryError",
]

