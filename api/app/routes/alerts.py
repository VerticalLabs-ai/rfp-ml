"""
Smart Alerts API endpoints.

Provides GovGPT-style alert management for RFP monitoring with customizable
rules, multi-channel notifications, and intelligent matching.
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_

from app.core.database import get_db
from app.dependencies import DBDep
from app.models.database import (
    AlertNotification,
    AlertPriority,
    AlertRule,
    AlertType,
    NotificationChannel,
    RFPOpportunity,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Models
# =============================================================================

class AlertRuleCreate(BaseModel):
    """Request to create a new alert rule."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    alert_type: AlertType
    priority: AlertPriority = AlertPriority.MEDIUM
    criteria: dict[str, Any] = Field(default_factory=dict)
    notification_channels: list[str] = Field(default=["in_app"])
    email_recipients: list[str] = Field(default_factory=list)
    webhook_url: str | None = None
    slack_channel: str | None = None
    cooldown_minutes: int = Field(default=60, ge=0, le=1440)
    max_alerts_per_day: int = Field(default=10, ge=1, le=100)
    company_profile_id: int | None = None


class AlertRuleUpdate(BaseModel):
    """Request to update an alert rule."""
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    priority: AlertPriority | None = None
    criteria: dict[str, Any] | None = None
    notification_channels: list[str] | None = None
    email_recipients: list[str] | None = None
    webhook_url: str | None = None
    slack_channel: str | None = None
    cooldown_minutes: int | None = None
    max_alerts_per_day: int | None = None


class NotificationAction(BaseModel):
    """Action to take on a notification."""
    action: str = Field(..., description="Action: mark_read, dismiss, action_taken")
    action_details: str | None = None


# =============================================================================
# Alert Rules Endpoints
# =============================================================================

@router.get("/rules")
async def list_alert_rules(
    db: DBDep,
    active_only: bool = Query(False, description="Only return active rules"),
    alert_type: AlertType | None = Query(None, description="Filter by alert type"),
):
    """
    List all alert rules.

    Returns configured alert rules with their criteria and notification settings.
    """
    query = db.query(AlertRule)

    if active_only:
        query = query.filter(AlertRule.is_active == True)

    if alert_type:
        query = query.filter(AlertRule.alert_type == alert_type)

    rules = query.order_by(AlertRule.created_at.desc()).all()

    return {
        "rules": [rule.to_dict() for rule in rules],
        "total": len(rules),
        "active_count": sum(1 for r in rules if r.is_active)
    }


@router.post("/rules")
async def create_alert_rule(db: DBDep, data: AlertRuleCreate):
    """
    Create a new alert rule.

    Configures monitoring for specific RFP conditions with customizable
    notification settings.
    """
    # Validate criteria based on alert type
    _validate_criteria(data.alert_type, data.criteria)

    rule = AlertRule(
        name=data.name,
        description=data.description,
        alert_type=data.alert_type,
        priority=data.priority,
        criteria=data.criteria,
        notification_channels=data.notification_channels,
        email_recipients=data.email_recipients,
        webhook_url=data.webhook_url,
        slack_channel=data.slack_channel,
        cooldown_minutes=data.cooldown_minutes,
        max_alerts_per_day=data.max_alerts_per_day,
        company_profile_id=data.company_profile_id,
    )

    db.add(rule)
    db.commit()
    db.refresh(rule)

    logger.info(f"Created alert rule: {rule.name} (type: {rule.alert_type.value})")

    return rule.to_dict()


@router.get("/rules/{rule_id}")
async def get_alert_rule(db: DBDep, rule_id: int):
    """Get a specific alert rule by ID."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    return rule.to_dict()


@router.patch("/rules/{rule_id}")
async def update_alert_rule(db: DBDep, rule_id: int, data: AlertRuleUpdate):
    """Update an existing alert rule."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    # Update fields that were provided
    update_data = data.model_dump(exclude_unset=True)

    if "criteria" in update_data:
        _validate_criteria(rule.alert_type, update_data["criteria"])

    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)

    logger.info(f"Updated alert rule: {rule.name}")

    return rule.to_dict()


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(db: DBDep, rule_id: int):
    """Delete an alert rule and its notifications."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    # Delete associated notifications
    db.query(AlertNotification).filter(AlertNotification.rule_id == rule_id).delete()

    db.delete(rule)
    db.commit()

    logger.info(f"Deleted alert rule: {rule.name}")

    return {"message": f"Alert rule '{rule.name}' deleted successfully"}


@router.post("/rules/{rule_id}/toggle")
async def toggle_alert_rule(db: DBDep, rule_id: int):
    """Toggle an alert rule active/inactive."""
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    rule.is_active = not rule.is_active
    rule.updated_at = datetime.utcnow()
    db.commit()

    status = "activated" if rule.is_active else "deactivated"
    logger.info(f"Alert rule {rule.name} {status}")

    return {
        "rule_id": rule.id,
        "name": rule.name,
        "is_active": rule.is_active,
        "message": f"Rule {status}"
    }


@router.post("/rules/{rule_id}/test")
async def test_alert_rule(db: DBDep, rule_id: int):
    """
    Test an alert rule against current RFPs.

    Returns matching RFPs without creating notifications.
    """
    rule = db.query(AlertRule).filter(AlertRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    matching_rfps = _find_matching_rfps(db, rule)

    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "alert_type": rule.alert_type.value,
        "criteria": rule.criteria,
        "matches_found": len(matching_rfps),
        "matching_rfps": [
            {
                "rfp_id": rfp.rfp_id,
                "title": rfp.title,
                "agency": rfp.agency,
                "score": rfp.triage_score
            }
            for rfp in matching_rfps[:10]  # Limit to 10 for preview
        ]
    }


# =============================================================================
# Notifications Endpoints
# =============================================================================

@router.get("/notifications")
async def list_notifications(
    db: DBDep,
    unread_only: bool = Query(False),
    priority: AlertPriority | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """
    List alert notifications.

    Returns notifications sorted by creation date (newest first).
    """
    query = db.query(AlertNotification)

    if unread_only:
        query = query.filter(AlertNotification.is_read == False)

    if priority:
        query = query.filter(AlertNotification.priority == priority)

    # Filter out dismissed
    query = query.filter(AlertNotification.is_dismissed == False)

    total = query.count()
    notifications = (
        query
        .order_by(AlertNotification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Get unread count
    unread_count = (
        db.query(AlertNotification)
        .filter(AlertNotification.is_read == False)
        .filter(AlertNotification.is_dismissed == False)
        .count()
    )

    return {
        "notifications": [n.to_dict() for n in notifications],
        "total": total,
        "unread_count": unread_count,
        "limit": limit,
        "offset": offset
    }


@router.get("/notifications/count")
async def get_notification_count(db: DBDep):
    """Get counts of notifications by status."""
    unread = (
        db.query(AlertNotification)
        .filter(AlertNotification.is_read == False)
        .filter(AlertNotification.is_dismissed == False)
        .count()
    )

    by_priority = dict(
        db.query(AlertNotification.priority, func.count(AlertNotification.id))
        .filter(AlertNotification.is_read == False)
        .filter(AlertNotification.is_dismissed == False)
        .group_by(AlertNotification.priority)
        .all()
    )

    return {
        "unread": unread,
        "by_priority": {
            "urgent": by_priority.get(AlertPriority.URGENT, 0),
            "high": by_priority.get(AlertPriority.HIGH, 0),
            "medium": by_priority.get(AlertPriority.MEDIUM, 0),
            "low": by_priority.get(AlertPriority.LOW, 0),
        }
    }


@router.get("/notifications/{notification_id}")
async def get_notification(db: DBDep, notification_id: int):
    """Get a specific notification."""
    notification = (
        db.query(AlertNotification)
        .filter(AlertNotification.id == notification_id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return notification.to_dict()


@router.post("/notifications/{notification_id}/action")
async def action_notification(
    db: DBDep,
    notification_id: int,
    data: NotificationAction
):
    """
    Perform an action on a notification.

    Actions: mark_read, dismiss, action_taken
    """
    notification = (
        db.query(AlertNotification)
        .filter(AlertNotification.id == notification_id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    if data.action == "mark_read":
        notification.is_read = True
        notification.read_at = datetime.utcnow()
    elif data.action == "dismiss":
        notification.is_dismissed = True
        notification.dismissed_at = datetime.utcnow()
    elif data.action == "action_taken":
        notification.is_actioned = True
        notification.action_taken = data.action_details
        notification.is_read = True
        notification.read_at = datetime.utcnow()
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {data.action}")

    db.commit()
    db.refresh(notification)

    return notification.to_dict()


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(db: DBDep):
    """Mark all unread notifications as read."""
    count = (
        db.query(AlertNotification)
        .filter(AlertNotification.is_read == False)
        .update({"is_read": True, "read_at": datetime.utcnow()})
    )
    db.commit()

    return {"marked_read": count}


@router.post("/notifications/dismiss-all")
async def dismiss_all_notifications(db: DBDep, older_than_days: int = Query(7, ge=1)):
    """Dismiss all read notifications older than specified days."""
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)

    count = (
        db.query(AlertNotification)
        .filter(AlertNotification.is_read == True)
        .filter(AlertNotification.created_at < cutoff)
        .filter(AlertNotification.is_dismissed == False)
        .update({"is_dismissed": True, "dismissed_at": datetime.utcnow()})
    )
    db.commit()

    return {"dismissed": count, "older_than_days": older_than_days}


# =============================================================================
# Alert Evaluation Endpoint
# =============================================================================

@router.post("/evaluate")
async def evaluate_alerts(db: DBDep, rfp_id: str | None = None):
    """
    Evaluate all active alert rules against RFPs.

    If rfp_id is provided, evaluates only against that RFP.
    Creates notifications for matching rules.
    """
    active_rules = (
        db.query(AlertRule)
        .filter(AlertRule.is_active == True)
        .all()
    )

    if not active_rules:
        return {"message": "No active alert rules", "notifications_created": 0}

    notifications_created = 0

    for rule in active_rules:
        # Check cooldown
        if not _check_cooldown(rule):
            continue

        # Check daily limit
        if not _check_daily_limit(db, rule):
            continue

        # Find matching RFPs
        if rfp_id:
            rfp = db.query(RFPOpportunity).filter(RFPOpportunity.rfp_id == rfp_id).first()
            matching_rfps = [rfp] if rfp and _matches_criteria(rfp, rule) else []
        else:
            matching_rfps = _find_matching_rfps(db, rule)

        # Create notifications
        for rfp in matching_rfps:
            # Check if notification already exists for this rule/rfp combo today
            existing = (
                db.query(AlertNotification)
                .filter(AlertNotification.rule_id == rule.id)
                .filter(AlertNotification.rfp_id == rfp.id)
                .filter(AlertNotification.created_at >= datetime.utcnow() - timedelta(days=1))
                .first()
            )

            if existing:
                continue

            notification = _create_notification(db, rule, rfp)
            notifications_created += 1

            # Update rule stats
            rule.triggered_count += 1
            rule.last_triggered_at = datetime.utcnow()

    db.commit()

    return {
        "rules_evaluated": len(active_rules),
        "notifications_created": notifications_created
    }


# =============================================================================
# Alert Types Info Endpoint
# =============================================================================

@router.get("/types")
async def list_alert_types():
    """
    List all available alert types with descriptions and criteria schemas.

    Useful for frontend to build dynamic rule creation forms.
    """
    alert_type_info = {
        AlertType.NEW_RFP.value: {
            "name": "New RFP",
            "description": "Alert when new RFPs match specified criteria",
            "criteria_schema": {
                "keywords": {"type": "array", "description": "Keywords to match in title/description"},
                "agencies": {"type": "array", "description": "Agencies to match"},
                "naics_codes": {"type": "array", "description": "NAICS codes to match"},
            }
        },
        AlertType.DEADLINE_APPROACHING.value: {
            "name": "Deadline Approaching",
            "description": "Alert when RFP deadlines are approaching",
            "criteria_schema": {
                "days_before": {"type": "integer", "description": "Days before deadline to alert", "default": 7}
            }
        },
        AlertType.STAGE_CHANGE.value: {
            "name": "Stage Change",
            "description": "Alert when RFPs move to specific pipeline stages",
            "criteria_schema": {
                "stages": {"type": "array", "description": "Pipeline stages to monitor"}
            }
        },
        AlertType.SCORE_THRESHOLD.value: {
            "name": "Score Threshold",
            "description": "Alert when RFP scores exceed threshold",
            "criteria_schema": {
                "min_score": {"type": "number", "description": "Minimum score to trigger alert"},
                "score_type": {"type": "string", "enum": ["triage", "overall"], "default": "triage"}
            }
        },
        AlertType.KEYWORD_MATCH.value: {
            "name": "Keyword Match",
            "description": "Alert when RFPs contain specific keywords",
            "criteria_schema": {
                "keywords": {"type": "array", "description": "Keywords to match"},
                "match_title": {"type": "boolean", "default": True},
                "match_description": {"type": "boolean", "default": True}
            }
        },
        AlertType.AGENCY_MATCH.value: {
            "name": "Agency Match",
            "description": "Alert for RFPs from specific agencies",
            "criteria_schema": {
                "agencies": {"type": "array", "description": "Agency names to match"}
            }
        },
        AlertType.NAICS_MATCH.value: {
            "name": "NAICS Match",
            "description": "Alert for RFPs with specific NAICS codes",
            "criteria_schema": {
                "naics_codes": {"type": "array", "description": "NAICS codes to match"}
            }
        },
        AlertType.DOCUMENT_UPDATED.value: {
            "name": "Document Updated",
            "description": "Alert when RFP documents are updated",
            "criteria_schema": {
                "document_types": {"type": "array", "description": "Document types to monitor"}
            }
        },
        AlertType.QA_POSTED.value: {
            "name": "Q&A Posted",
            "description": "Alert when new Q&A responses are posted",
            "criteria_schema": {}
        },
        AlertType.AWARD_ANNOUNCED.value: {
            "name": "Award Announced",
            "description": "Alert when contract awards are announced",
            "criteria_schema": {}
        },
    }

    return {
        "alert_types": alert_type_info,
        "priorities": [p.value for p in AlertPriority],
        "notification_channels": [c.value for c in NotificationChannel]
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _validate_criteria(alert_type: AlertType, criteria: dict[str, Any]):
    """Validate criteria based on alert type."""
    if alert_type == AlertType.DEADLINE_APPROACHING:
        if "days_before" in criteria:
            if not isinstance(criteria["days_before"], int) or criteria["days_before"] < 1:
                raise HTTPException(
                    status_code=400,
                    detail="days_before must be a positive integer"
                )

    if alert_type == AlertType.SCORE_THRESHOLD:
        if "min_score" in criteria:
            if not isinstance(criteria["min_score"], (int, float)):
                raise HTTPException(
                    status_code=400,
                    detail="min_score must be a number"
                )


def _check_cooldown(rule: AlertRule) -> bool:
    """Check if rule cooldown has passed."""
    if not rule.last_triggered_at:
        return True

    cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
    return datetime.utcnow() >= rule.last_triggered_at + cooldown_delta


def _check_daily_limit(db, rule: AlertRule) -> bool:
    """Check if rule has exceeded daily limit."""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    today_count = (
        db.query(AlertNotification)
        .filter(AlertNotification.rule_id == rule.id)
        .filter(AlertNotification.created_at >= today_start)
        .count()
    )

    return today_count < rule.max_alerts_per_day


def _find_matching_rfps(db, rule: AlertRule) -> list[RFPOpportunity]:
    """Find RFPs matching rule criteria."""
    query = db.query(RFPOpportunity)
    criteria = rule.criteria

    if rule.alert_type == AlertType.KEYWORD_MATCH:
        keywords = criteria.get("keywords", [])
        if keywords:
            conditions = []
            for kw in keywords:
                if criteria.get("match_title", True):
                    conditions.append(RFPOpportunity.title.ilike(f"%{kw}%"))
                if criteria.get("match_description", True):
                    conditions.append(RFPOpportunity.description.ilike(f"%{kw}%"))
            if conditions:
                query = query.filter(or_(*conditions))

    elif rule.alert_type == AlertType.AGENCY_MATCH:
        agencies = criteria.get("agencies", [])
        if agencies:
            query = query.filter(RFPOpportunity.agency.in_(agencies))

    elif rule.alert_type == AlertType.NAICS_MATCH:
        naics_codes = criteria.get("naics_codes", [])
        if naics_codes:
            query = query.filter(RFPOpportunity.naics_code.in_(naics_codes))

    elif rule.alert_type == AlertType.DEADLINE_APPROACHING:
        days_before = criteria.get("days_before", 7)
        deadline = datetime.utcnow() + timedelta(days=days_before)
        query = query.filter(
            and_(
                RFPOpportunity.response_deadline != None,
                RFPOpportunity.response_deadline <= deadline,
                RFPOpportunity.response_deadline >= datetime.utcnow()
            )
        )

    elif rule.alert_type == AlertType.SCORE_THRESHOLD:
        min_score = criteria.get("min_score", 0.7)
        score_type = criteria.get("score_type", "triage")
        if score_type == "overall":
            query = query.filter(RFPOpportunity.overall_score >= min_score)
        else:
            query = query.filter(RFPOpportunity.triage_score >= min_score)

    elif rule.alert_type == AlertType.STAGE_CHANGE:
        stages = criteria.get("stages", [])
        if stages:
            query = query.filter(RFPOpportunity.current_stage.in_(stages))

    return query.limit(100).all()


def _matches_criteria(rfp: RFPOpportunity, rule: AlertRule) -> bool:
    """Check if single RFP matches rule criteria."""
    criteria = rule.criteria

    if rule.alert_type == AlertType.KEYWORD_MATCH:
        keywords = criteria.get("keywords", [])
        text = ""
        if criteria.get("match_title", True):
            text += (rfp.title or "").lower()
        if criteria.get("match_description", True):
            text += " " + (rfp.description or "").lower()
        return any(kw.lower() in text for kw in keywords)

    elif rule.alert_type == AlertType.AGENCY_MATCH:
        return rfp.agency in criteria.get("agencies", [])

    elif rule.alert_type == AlertType.NAICS_MATCH:
        return rfp.naics_code in criteria.get("naics_codes", [])

    elif rule.alert_type == AlertType.SCORE_THRESHOLD:
        min_score = criteria.get("min_score", 0.7)
        score_type = criteria.get("score_type", "triage")
        score = rfp.overall_score if score_type == "overall" else rfp.triage_score
        return score is not None and score >= min_score

    return True


def _create_notification(
    db,
    rule: AlertRule,
    rfp: RFPOpportunity
) -> AlertNotification:
    """Create a notification for a rule/RFP match."""
    # Build notification title and message
    title = _build_notification_title(rule, rfp)
    message = _build_notification_message(rule, rfp)

    notification = AlertNotification(
        rule_id=rule.id,
        rfp_id=rfp.id,
        title=title,
        message=message,
        priority=rule.priority,
        delivery_status={"in_app": "delivered"},
        context_data={
            "rule_name": rule.name,
            "alert_type": rule.alert_type.value,
            "rfp_title": rfp.title,
            "criteria_matched": rule.criteria
        }
    )

    db.add(notification)
    return notification


def _build_notification_title(rule: AlertRule, rfp: RFPOpportunity) -> str:
    """Build notification title based on alert type."""
    score_display = f"{rfp.triage_score:.0%}" if rfp.triage_score is not None else "N/A"
    titles = {
        AlertType.NEW_RFP: f"New RFP: {rfp.title[:50]}...",
        AlertType.DEADLINE_APPROACHING: f"Deadline Alert: {rfp.title[:40]}...",
        AlertType.STAGE_CHANGE: f"Stage Update: {rfp.current_stage.value}",
        AlertType.SCORE_THRESHOLD: f"High Score RFP: {score_display}",
        AlertType.KEYWORD_MATCH: f"Keyword Match: {rfp.title[:45]}...",
        AlertType.AGENCY_MATCH: f"{rfp.agency or 'Unknown'}: New Opportunity",
        AlertType.NAICS_MATCH: f"NAICS {rfp.naics_code or 'N/A'}: {rfp.title[:35]}...",
        AlertType.DOCUMENT_UPDATED: f"Document Update: {rfp.title[:40]}...",
        AlertType.QA_POSTED: f"Q&A Posted: {rfp.title[:45]}...",
        AlertType.AWARD_ANNOUNCED: f"Award: {rfp.title[:50]}...",
    }
    return titles.get(rule.alert_type, f"Alert: {rfp.title[:50]}...")


def _build_notification_message(rule: AlertRule, rfp: RFPOpportunity) -> str:
    """Build notification message based on alert type."""
    if rule.alert_type == AlertType.DEADLINE_APPROACHING:
        days = (rfp.response_deadline - datetime.utcnow()).days if rfp.response_deadline else 0
        return f"RFP deadline is in {days} days. Agency: {rfp.agency}. Review and take action."

    if rule.alert_type == AlertType.SCORE_THRESHOLD:
        score_str = f"{rfp.triage_score:.0%}" if rfp.triage_score is not None else "N/A"
        return f"This RFP scored {score_str} on triage. Consider prioritizing this opportunity from {rfp.agency or 'unknown agency'}."

    if rule.alert_type == AlertType.KEYWORD_MATCH:
        keywords = rule.criteria.get("keywords", [])
        return f"Matched keywords: {', '.join(keywords[:3])}. Agency: {rfp.agency}."

    return f"Alert triggered by rule '{rule.name}' for RFP from {rfp.agency}. Review for relevance."
