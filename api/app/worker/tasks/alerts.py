"""
Alert tasks for Celery.

Handles:
- Periodic alert rule evaluation
- Email notification delivery
"""

import asyncio
import logging
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from celery import shared_task

# Add project paths
project_root = str(Path(__file__).parents[5])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


def broadcast_alert(notification: dict):
    """Broadcast alert notification via WebSocket."""
    try:
        from api.app.websockets.channels import broadcast_alert_notification

        asyncio.run(broadcast_alert_notification(notification))
    except Exception as e:
        logger.warning(f"Failed to broadcast alert: {e}")


@shared_task(bind=True, name="api.app.worker.tasks.alerts.evaluate_alert_rules")
def evaluate_alert_rules(self, rfp_id: str | None = None) -> dict:
    """
    Evaluate all active alert rules against RFPs.

    This task is scheduled to run periodically (every 15 minutes by default).
    Can also be triggered manually for a specific RFP.

    Args:
        rfp_id: Optional specific RFP to evaluate against

    Returns:
        Dict with evaluation results
    """
    logger.info(f"Evaluating alert rules - RFP: {rfp_id or 'all'}")

    try:
        from datetime import datetime, timedelta, timezone

        from api.app.core.database import SessionLocal
        from api.app.models.database import AlertNotification, AlertRule, RFPOpportunity

        with SessionLocal() as db:
            # Get active rules
            rules = db.query(AlertRule).filter(AlertRule.is_active).all()

            if not rules:
                return {
                    "status": "success",
                    "rules_evaluated": 0,
                    "notifications_created": 0,
                }

            # Get RFPs to evaluate
            if rfp_id:
                rfps = (
                    db.query(RFPOpportunity)
                    .filter(RFPOpportunity.rfp_id == rfp_id)
                    .all()
                )
            else:
                # Get RFPs from last 24 hours (for periodic evaluation)
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                rfps = (
                    db.query(RFPOpportunity)
                    .filter(RFPOpportunity.created_at >= cutoff)
                    .all()
                )

            notifications_created = 0

            for rule in rules:
                try:
                    # Check cooldown
                    if rule.last_triggered_at:
                        cooldown = timedelta(minutes=rule.cooldown_minutes or 60)
                        if (
                            datetime.now(timezone.utc) - rule.last_triggered_at
                            < cooldown
                        ):
                            continue

                    # Check daily limit
                    if rule.max_alerts_per_day:
                        today_start = datetime.now(timezone.utc).replace(
                            hour=0, minute=0, second=0, microsecond=0
                        )
                        today_count = (
                            db.query(AlertNotification)
                            .filter(
                                AlertNotification.rule_id == rule.id,
                                AlertNotification.created_at >= today_start,
                            )
                            .count()
                        )
                        if today_count >= rule.max_alerts_per_day:
                            continue

                    # Evaluate rule against RFPs
                    for rfp in rfps:
                        if _matches_rule(rule, rfp):
                            # Check if notification already exists
                            existing = (
                                db.query(AlertNotification)
                                .filter(
                                    AlertNotification.rule_id == rule.id,
                                    AlertNotification.rfp_id == rfp.id,
                                    AlertNotification.is_dismissed is False,
                                )
                                .first()
                            )

                            if existing:
                                continue

                            # Create notification
                            notification = AlertNotification(
                                rule_id=rule.id,
                                rfp_id=rfp.id,
                                title=_build_notification_title(rule, rfp),
                                message=_build_notification_message(rule, rfp),
                                priority=rule.priority,
                                delivery_status={"in_app": "delivered"},
                            )
                            db.add(notification)

                            # Update rule
                            rule.triggered_count = (rule.triggered_count or 0) + 1
                            rule.last_triggered_at = datetime.now(timezone.utc)

                            notifications_created += 1

                            # Trigger email if configured
                            if (
                                "email" in (rule.notification_channels or [])
                                and rule.email_recipients
                            ):
                                db.flush()  # Get notification ID
                                send_alert_email.delay(
                                    notification.id, rule.email_recipients
                                )

                            # Broadcast to WebSocket
                            broadcast_alert(
                                {
                                    "id": notification.id,
                                    "title": notification.title,
                                    "message": notification.message,
                                    "priority": (
                                        notification.priority.value
                                        if notification.priority
                                        else "medium"
                                    ),
                                    "rfp_id": rfp.rfp_id,
                                }
                            )

                except Exception as e:
                    logger.error(f"Error evaluating rule {rule.id}: {e}")
                    continue

            db.commit()

            return {
                "status": "success",
                "rules_evaluated": len(rules),
                "rfps_checked": len(rfps),
                "notifications_created": notifications_created,
            }

    except Exception as e:
        logger.exception("Alert evaluation failed")
        return {"status": "error", "error": str(e)}


def _matches_rule(rule, rfp) -> bool:
    """Check if an RFP matches a rule's criteria."""
    criteria = rule.criteria or {}
    alert_type = rule.alert_type

    # Import AlertType enum
    from api.app.models.database import AlertType

    if alert_type == AlertType.NEW_RFP:
        # New RFPs match if they meet optional criteria
        pass

    elif alert_type == AlertType.KEYWORD_MATCH:
        keywords = criteria.get("keywords", [])
        if keywords:
            text = f"{rfp.title or ''} {rfp.description or ''}".lower()
            if not any(kw.lower() in text for kw in keywords):
                return False

    elif alert_type == AlertType.AGENCY_MATCH:
        agencies = criteria.get("agencies", [])
        if agencies and rfp.agency not in agencies:
            return False

    elif alert_type == AlertType.NAICS_MATCH:
        naics_codes = criteria.get("naics_codes", [])
        if naics_codes and rfp.naics_code not in naics_codes:
            return False

    elif alert_type == AlertType.SCORE_THRESHOLD:
        min_score = criteria.get("min_score", 0)
        if (rfp.triage_score or 0) < min_score:
            return False

    elif alert_type == AlertType.DEADLINE_APPROACHING:
        from datetime import datetime, timedelta, timezone

        days = criteria.get("days_before", 7)
        if rfp.response_deadline:
            deadline = rfp.response_deadline
            if isinstance(deadline, str):
                deadline = datetime.fromisoformat(deadline)
            if deadline - datetime.now(timezone.utc) > timedelta(days=days):
                return False
        else:
            return False

    return True


def _build_notification_title(rule, rfp) -> str:
    """Build notification title."""
    title = rfp.title or "Untitled RFP"
    return f"{rule.name}: {title[:50]}"


def _build_notification_message(rule, rfp) -> str:
    """Build notification message."""
    parts = [f"RFP: {rfp.title}"]
    if rfp.agency:
        parts.append(f"Agency: {rfp.agency}")
    if rfp.response_deadline:
        parts.append(f"Deadline: {rfp.response_deadline}")
    if rfp.triage_score:
        parts.append(f"Score: {rfp.triage_score}")
    return " | ".join(parts)


@shared_task(bind=True, name="api.app.worker.tasks.alerts.send_alert_email")
def send_alert_email(self, notification_id: int, recipients: list[str]) -> dict:
    """
    Send alert notification email.

    Args:
        notification_id: ID of the notification to send
        recipients: List of email addresses

    Returns:
        Dict with send status
    """
    logger.info(
        "Sending alert email - Notification: %s, Recipients: %s",
        notification_id,
        recipients,
    )

    try:
        from api.app.core.config import settings
        from api.app.core.database import SessionLocal
        from api.app.models.database import AlertNotification, RFPOpportunity

        # Load notification
        with SessionLocal() as db:
            notification = (
                db.query(AlertNotification)
                .filter(AlertNotification.id == notification_id)
                .first()
            )

            if not notification:
                return {"status": "error", "error": "Notification not found"}

            rfp = (
                db.query(RFPOpportunity)
                .filter(RFPOpportunity.id == notification.rfp_id)
                .first()
            )

            # Build email content
            subject = notification.title
            html_content = _render_email_template(notification, rfp)
            text_content = f"{notification.title}\n\n{notification.message}"

            # Send email
            sent = False

            # Try SendGrid first
            sendgrid_key = os.getenv("SENDGRID_API_KEY")
            if sendgrid_key:
                sent = _send_via_sendgrid(
                    recipients, subject, html_content, sendgrid_key
                )

            # Fall back to SMTP
            if not sent and settings.SMTP_HOST:
                sent = _send_via_smtp(
                    recipients, subject, html_content, text_content, settings
                )

            # Update delivery status
            if sent:
                notification.delivery_status = notification.delivery_status or {}
                notification.delivery_status["email"] = "delivered"
                db.commit()
                return {"status": "success", "recipients": recipients}
            else:
                notification.delivery_status = notification.delivery_status or {}
                notification.delivery_status["email"] = "failed"
                db.commit()
                return {"status": "error", "error": "Failed to send email"}

    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return {"status": "error", "error": str(e)}


def _render_email_template(notification, rfp) -> str:
    """Render HTML email template."""
    app_url = os.getenv("APP_URL", "http://localhost:3300")

    return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #1a1a2e; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px; }}
        .button {{ display: inline-block; background: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 15px; }}
        .footer {{ margin-top: 20px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2 style="margin: 0;">{notification.title}</h2>
        </div>
        <div class="content">
            <p>{notification.message}</p>

            {f'''
            <h3>RFP Details</h3>
            <ul>
                <li><strong>Title:</strong> {rfp.title if rfp else 'N/A'}</li>
                <li><strong>Agency:</strong> {rfp.agency if rfp else 'N/A'}</li>
                <li><strong>Deadline:</strong> {rfp.response_deadline if rfp else 'N/A'}</li>
            </ul>
            ''' if rfp else ''}

            <a href="{app_url}/rfp/{rfp.rfp_id if rfp else ''}" class="button">
                View RFP Details
            </a>
        </div>
        <div class="footer">
            <p>This is an automated alert from your RFP Bid Generation System.</p>
            <p>To manage your alerts, visit <a href="{app_url}/alerts">Alert Settings</a>.</p>
        </div>
    </div>
</body>
</html>
"""


def _send_via_sendgrid(
    recipients: list[str], subject: str, html_content: str, api_key: str
) -> bool:
    """Send email via SendGrid API."""
    import httpx

    try:
        from_email = os.getenv("EMAIL_FROM", "noreply@rfpbid.com")

        response = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": e} for e in recipients]}],
                "from": {"email": from_email},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_content}],
            },
            timeout=30.0,
        )
        return response.status_code == 202
    except Exception as e:
        logger.error(f"SendGrid send failed: {e}")
        return False


def _send_via_smtp(
    recipients: list[str], subject: str, html_content: str, text_content: str, settings
) -> bool:
    """Send email via SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = ", ".join(recipients)

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, recipients, msg.as_string())

        return True
    except Exception as e:
        logger.error(f"SMTP send failed: {e}")
        return False
