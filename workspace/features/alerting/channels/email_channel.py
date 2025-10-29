"""
Email Alert Channel

Sends alerts via SMTP email.

Supports:
- HTML and plain text emails
- Multiple recipients
- Configurable SMTP server
- TLS/SSL support

Author: DevOps Engineer (Agent C)
Date: 2025-10-29
Sprint: Sprint 2 Stream C
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from ..alert_service import AlertChannel
from ..models import Alert, AlertSeverity

logger = logging.getLogger(__name__)


class EmailAlertChannel(AlertChannel):
    """
    Email alert channel

    Sends alerts via SMTP.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: List[str],
        use_tls: bool = True,
    ):
        """
        Initialize email channel

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_email: Sender email address
            to_emails: List of recipient email addresses
            use_tls: Use TLS encryption (default: True)
        """
        super().__init__(name="email")
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

        logger.info(
            f"Email channel initialized: {smtp_host}:{smtp_port} "
            f"from={from_email} to={len(to_emails)} recipients"
        )

    async def send(self, alert: Alert) -> bool:
        """
        Send email alert

        Args:
            alert: Alert to send

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['From'] = self.from_email
            message['To'] = ", ".join(self.to_emails)
            message['Subject'] = f"[{alert.severity.upper()}] {alert.title}"

            # Plain text body
            text_body = self._format_text_body(alert)
            text_part = MIMEText(text_body, 'plain')
            message.attach(text_part)

            # HTML body
            html_body = self._format_html_body(alert)
            html_part = MIMEText(html_body, 'html')
            message.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                server.login(self.username, self.password)
                server.send_message(message)

            logger.info(f"Email alert sent: {alert.title}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}", exc_info=True)
            return False

    def _format_text_body(self, alert: Alert) -> str:
        """Format plain text email body"""
        body = f"""
Trading System Alert
{'=' * 50}

Alert: {alert.title}
Severity: {alert.severity.upper()}
Category: {alert.category}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{alert.message}
"""

        # Add metadata if present
        if alert.metadata:
            body += "\n\nAdditional Information:\n"
            for key, value in alert.metadata.items():
                body += f"  {key}: {value}\n"

        body += f"""
{'=' * 50}
Alert ID: {alert.id}
"""
        return body

    def _format_html_body(self, alert: Alert) -> str:
        """Format HTML email body"""
        # Color based on severity
        severity_colors = {
            AlertSeverity.INFO: "#3498db",      # Blue
            AlertSeverity.WARNING: "#f39c12",   # Orange
            AlertSeverity.CRITICAL: "#e74c3c",  # Red
        }
        color = severity_colors.get(alert.severity, "#95a5a6")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background-color: {color};
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
        }}
        .content {{
            border: 1px solid #ddd;
            border-top: none;
            padding: 20px;
            background-color: #f9f9f9;
        }}
        .info-row {{
            margin: 10px 0;
        }}
        .label {{
            font-weight: bold;
            display: inline-block;
            width: 100px;
        }}
        .message {{
            background-color: white;
            padding: 15px;
            border-left: 4px solid {color};
            margin: 15px 0;
        }}
        .metadata {{
            background-color: #fff;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }}
        .footer {{
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
            font-size: 0.9em;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h2>{alert.severity.upper()}: {alert.title}</h2>
    </div>
    <div class="content">
        <div class="info-row">
            <span class="label">Category:</span>
            <span>{alert.category}</span>
        </div>
        <div class="info-row">
            <span class="label">Time:</span>
            <span>{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</span>
        </div>

        <div class="message">
            <strong>Message:</strong><br>
            {alert.message.replace('\n', '<br>')}
        </div>
"""

        # Add metadata if present
        if alert.metadata:
            html += """
        <div class="metadata">
            <strong>Additional Information:</strong><br>
            <ul>
"""
            for key, value in alert.metadata.items():
                html += f"                <li><strong>{key}:</strong> {value}</li>\n"

            html += """
            </ul>
        </div>
"""

        html += f"""
        <div class="footer">
            Alert ID: {alert.id}<br>
            Trading System Automated Alert
        </div>
    </div>
</body>
</html>
"""
        return html


# Export
__all__ = ["EmailAlertChannel"]
