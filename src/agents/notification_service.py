"""
Notification service for submission updates and alerts.
"""
import os
import logging
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationChannel(Enum):
    """Notification channel types."""
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationService:
    """Service for sending notifications about submission events."""

    def __init__(
        self,
        enabled_channels: Optional[List[str]] = None,
        smtp_config: Optional[Dict] = None,
        slack_webhook: Optional[str] = None
    ):
        """
        Initialize notification service.

        Args:
            enabled_channels: List of enabled notification channels
            smtp_config: SMTP configuration for email
            slack_webhook: Slack webhook URL
        """
        self.enabled_channels = enabled_channels or ["email"]
        self.smtp_config = smtp_config or {}
        self.slack_webhook = slack_webhook or os.getenv("SLACK_WEBHOOK_URL")

        # Initialize channels
        self.channels = {}
        self._initialize_channels()

        logger.info(f"NotificationService initialized with channels: {self.enabled_channels}")

    def _initialize_channels(self):
        """Initialize notification channels."""
        if "email" in self.enabled_channels:
            try:
                self.channels["email"] = EmailChannel(self.smtp_config)
            except Exception as e:
                logger.warning(f"Could not initialize email channel: {e}")

        if "slack" in self.enabled_channels and self.slack_webhook:
            try:
                self.channels["slack"] = SlackChannel(self.slack_webhook)
            except Exception as e:
                logger.warning(f"Could not initialize Slack channel: {e}")

    def send_notification(
        self,
        subject: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        channels: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Send notification through configured channels.

        Args:
            subject: Notification subject
            message: Notification message
            priority: Priority level
            channels: Specific channels to use (None = all enabled)
            metadata: Additional metadata
        """
        target_channels = channels or self.enabled_channels

        for channel_name in target_channels:
            channel = self.channels.get(channel_name)
            if channel:
                try:
                    channel.send(subject, message, priority, metadata)
                    logger.info(f"Notification sent via {channel_name}: {subject}")
                except Exception as e:
                    logger.error(f"Failed to send notification via {channel_name}: {e}")

    def send_submission_queued(self, rfp_id: str, portal: str):
        """Send notification when submission is queued."""
        self.send_notification(
            "Submission Queued",
            f"Bid for RFP {rfp_id} has been queued for submission to {portal}",
            priority=NotificationPriority.LOW
        )

    def send_submission_successful(self, rfp_id: str, portal: str, confirmation: str):
        """Send notification when submission succeeds."""
        self.send_notification(
            "Submission Successful ✅",
            f"Bid for RFP {rfp_id} successfully submitted to {portal}. Confirmation: {confirmation}",
            priority=NotificationPriority.HIGH
        )

    def send_submission_failed(self, rfp_id: str, portal: str, error: str):
        """Send notification when submission fails."""
        self.send_notification(
            "Submission Failed ❌",
            f"Bid for RFP {rfp_id} failed to submit to {portal}. Error: {error}",
            priority=NotificationPriority.CRITICAL
        )

    def send_deadline_warning(self, rfp_id: str, hours_remaining: int):
        """Send notification for approaching deadline."""
        self.send_notification(
            "Deadline Warning ⚠️",
            f"RFP {rfp_id} deadline in {hours_remaining} hours",
            priority=NotificationPriority.HIGH
        )


class EmailChannel:
    """Email notification channel."""

    def __init__(self, smtp_config: Dict):
        """Initialize email channel."""
        self.smtp_host = smtp_config.get("host", os.getenv("SMTP_HOST"))
        self.smtp_port = smtp_config.get("port", int(os.getenv("SMTP_PORT", 587)))
        self.smtp_user = smtp_config.get("user", os.getenv("SMTP_USER"))
        self.smtp_password = smtp_config.get("password", os.getenv("SMTP_PASSWORD"))
        self.from_email = smtp_config.get("from_email", "noreply@rfpbid.com")
        self.recipients = smtp_config.get("recipients", ["team@company.com"])

    def send(
        self,
        subject: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict] = None
    ):
        """Send email notification."""
        # In production, use actual SMTP
        # import smtplib
        # from email.mime.text import MIMEText
        #
        # msg = MIMEText(message)
        # msg['Subject'] = subject
        # msg['From'] = self.from_email
        # msg['To'] = ', '.join(self.recipients)
        #
        # with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
        #     server.starttls()
        #     server.login(self.smtp_user, self.smtp_password)
        #     server.send_message(msg)

        logger.info(f"Email notification: {subject} - {message}")


class SlackChannel:
    """Slack notification channel."""

    def __init__(self, webhook_url: str):
        """Initialize Slack channel."""
        self.webhook_url = webhook_url

    def send(
        self,
        subject: str,
        message: str,
        priority: NotificationPriority,
        metadata: Optional[Dict] = None
    ):
        """Send Slack notification."""
        # In production, use actual Slack webhook
        # import requests
        #
        # payload = {
        #     "text": f"*{subject}*\n{message}",
        #     "username": "RFP Bid System",
        #     "icon_emoji": ":robot_face:"
        # }
        #
        # requests.post(self.webhook_url, json=payload)

        logger.info(f"Slack notification: {subject} - {message}")
