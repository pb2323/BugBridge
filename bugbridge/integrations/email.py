"""
Email Delivery Service

Handles sending reports and notifications via email using SMTP.
"""

from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

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
        if MARKDOWN_AVAILABLE:
            html_body = markdown.markdown(
                report_content,
                extensions=['extra', 'tables', 'fenced_code']
            )
        else:
            # Fallback: simple markdown-like conversion
            html_body = self._simple_markdown_to_html(report_content)
        
        # Wrap in styled HTML template
        html_email = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #4F46E5;
            border-bottom: 3px solid #4F46E5;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        h2 {{
            color: #1F2937;
            margin-top: 30px;
            border-bottom: 2px solid #E5E7EB;
            padding-bottom: 8px;
        }}
        h3 {{
            color: #374151;
            margin-top: 20px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #E5E7EB;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #F9FAFB;
            font-weight: 600;
            color: #1F2937;
        }}
        tr:nth-child(even) {{
            background-color: #F9FAFB;
        }}
        ul, ol {{
            margin: 10px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 5px 0;
        }}
        code {{
            background-color: #F3F4F6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #F3F4F6;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        blockquote {{
            border-left: 4px solid #4F46E5;
            padding-left: 20px;
            margin: 20px 0;
            color: #6B7280;
            font-style: italic;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #E5E7EB;
            color: #6B7280;
            font-size: 0.9em;
            text-align: center;
        }}
        strong {{
            color: #1F2937;
        }}
    </style>
</head>
<body>
    <div class="container">
        {html_body}
        <div class="footer">
            <p>This is an automated report from BugBridge.</p>
            <p>Generated on {report_date}</p>
        </div>
    </div>
</body>
</html>"""

        # Create plain text version as fallback
        plain_text = f"""BugBridge Daily Summary Report - {report_date}

{report_content}

---
This is an automated report from BugBridge.
Generated on {report_date}
"""

        # Send both HTML and plain text versions
        self._send_multipart_email(
            to_emails=to_emails,
            subject=subject,
            html_body=html_email,
            plain_body=plain_text,
            from_email=from_email,
        )

    def _simple_markdown_to_html(self, markdown_text: str) -> str:
        """Simple markdown to HTML converter (fallback when markdown library not available)."""
        import re
        
        html = markdown_text
        
        # Headers
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        
        # Bold
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.+?)__', r'<strong>\1</strong>', html)
        
        # Italic
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.+?)_', r'<em>\1</em>', html)
        
        # Code blocks
        html = re.sub(r'```(.+?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)
        
        # Links
        html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
        
        # Lists (simple)
        lines = html.split('\n')
        in_list = False
        result = []
        for line in lines:
            if line.strip().startswith('- ') or line.strip().startswith('* '):
                if not in_list:
                    result.append('<ul>')
                    in_list = True
                result.append(f'<li>{line.strip()[2:]}</li>')
            else:
                if in_list:
                    result.append('</ul>')
                    in_list = False
                if line.strip():
                    result.append(f'<p>{line}</p>')
                else:
                    result.append('')
        if in_list:
            result.append('</ul>')
        html = '\n'.join(result)
        
        return html

    def _send_multipart_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        plain_body: str,
        from_email: Optional[str] = None,
    ) -> None:
        """
        Send email with both HTML and plain text versions.

        Args:
            to_emails: List of recipient email addresses.
            subject: Email subject line.
            html_body: HTML email body.
            plain_body: Plain text email body (fallback).
            from_email: Sender email address (optional).

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

        # Add both plain text and HTML versions
        msg.attach(MIMEText(plain_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        try:
            logger.info(
                f"Sending HTML email to {len(to_emails)} recipient(s)",
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
                f"Successfully sent HTML email to {len(to_emails)} recipient(s)",
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


__all__ = [
    "EmailService",
    "EmailDeliveryError",
]

