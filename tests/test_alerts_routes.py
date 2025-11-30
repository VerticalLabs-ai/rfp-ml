"""
Unit tests for Smart Alerts API routes.

Tests the alert management functionality including:
- Alert rule CRUD operations
- Notification management
- Alert evaluation and matching
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from app.models.database import (
    AlertRule,
    AlertNotification,
    AlertType,
    AlertPriority,
    RFPOpportunity,
    PipelineStage,
)
from app.routes.alerts import (
    AlertRuleCreate,
    AlertRuleUpdate,
    NotificationAction,
    _validate_criteria,
    _check_cooldown,
    _check_daily_limit,
    _find_matching_rfps,
    _matches_criteria,
    _create_notification,
    _build_notification_title,
    _build_notification_message,
)


class TestAlertRuleModels:
    """Tests for alert rule Pydantic models."""

    def test_alert_rule_create_basic(self):
        """Test basic AlertRuleCreate model."""
        rule = AlertRuleCreate(
            name="Test Rule",
            alert_type=AlertType.KEYWORD_MATCH,
            criteria={"keywords": ["cloud"]}
        )
        assert rule.name == "Test Rule"
        assert rule.priority == AlertPriority.MEDIUM
        assert rule.cooldown_minutes == 60

    def test_alert_rule_create_full(self):
        """Test AlertRuleCreate with all fields."""
        rule = AlertRuleCreate(
            name="Full Rule",
            description="A complete rule",
            alert_type=AlertType.DEADLINE_APPROACHING,
            priority=AlertPriority.URGENT,
            criteria={"days_before": 7},
            notification_channels=["in_app", "email"],
            email_recipients=["user@example.com"],
            webhook_url="https://hooks.example.com/alert",
            cooldown_minutes=30,
            max_alerts_per_day=5
        )
        assert rule.max_alerts_per_day == 5
        assert len(rule.notification_channels) == 2

    def test_alert_rule_update_partial(self):
        """Test partial AlertRuleUpdate."""
        update = AlertRuleUpdate(name="New Name")
        assert update.name == "New Name"
        assert update.is_active is None
        assert update.priority is None

    def test_notification_action_model(self):
        """Test NotificationAction model."""
        action = NotificationAction(action="mark_read")
        assert action.action == "mark_read"
        assert action.action_details is None


class TestValidateCriteria:
    """Tests for criteria validation helper."""

    def test_validate_deadline_approaching_valid(self):
        """Test valid deadline approaching criteria."""
        _validate_criteria(
            AlertType.DEADLINE_APPROACHING,
            {"days_before": 7}
        )  # Should not raise

    def test_validate_deadline_approaching_invalid(self):
        """Test invalid deadline approaching criteria."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_criteria(
                AlertType.DEADLINE_APPROACHING,
                {"days_before": -1}
            )
        assert exc_info.value.status_code == 400

    def test_validate_score_threshold_valid(self):
        """Test valid score threshold criteria."""
        _validate_criteria(
            AlertType.SCORE_THRESHOLD,
            {"min_score": 0.75}
        )  # Should not raise

    def test_validate_score_threshold_invalid(self):
        """Test invalid score threshold criteria."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_criteria(
                AlertType.SCORE_THRESHOLD,
                {"min_score": "not_a_number"}
            )
        assert exc_info.value.status_code == 400


class TestCheckCooldown:
    """Tests for cooldown check helper."""

    def test_cooldown_not_triggered_before(self):
        """Test cooldown passes when rule never triggered."""
        rule = MagicMock()
        rule.last_triggered_at = None
        rule.cooldown_minutes = 60

        assert _check_cooldown(rule) is True

    def test_cooldown_passed(self):
        """Test cooldown passes after enough time."""
        rule = MagicMock()
        rule.last_triggered_at = datetime.utcnow() - timedelta(hours=2)
        rule.cooldown_minutes = 60

        assert _check_cooldown(rule) is True

    def test_cooldown_not_passed(self):
        """Test cooldown fails when triggered recently."""
        rule = MagicMock()
        rule.last_triggered_at = datetime.utcnow() - timedelta(minutes=30)
        rule.cooldown_minutes = 60

        assert _check_cooldown(rule) is False


class TestCheckDailyLimit:
    """Tests for daily limit check helper."""

    def test_daily_limit_not_exceeded(self, db_session, sample_alert_rule):
        """Test daily limit not exceeded."""
        assert _check_daily_limit(db_session, sample_alert_rule) is True

    def test_daily_limit_exceeded(self, db_session, sample_alert_rule, sample_rfp):
        """Test daily limit exceeded."""
        # Create max_alerts_per_day notifications today
        for i in range(sample_alert_rule.max_alerts_per_day):
            notification = AlertNotification(
                rule_id=sample_alert_rule.id,
                rfp_id=sample_rfp.id,
                title=f"Test {i}",
                message="Test message",
                priority=AlertPriority.MEDIUM,
            )
            db_session.add(notification)
        db_session.commit()

        assert _check_daily_limit(db_session, sample_alert_rule) is False


class TestMatchesCriteria:
    """Tests for single RFP criteria matching."""

    @pytest.fixture
    def sample_rfp_obj(self):
        """Create sample RFP object."""
        rfp = MagicMock()
        rfp.title = "Cloud Computing Services"
        rfp.description = "Cybersecurity and cloud infrastructure"
        rfp.agency = "Department of Defense"
        rfp.naics_code = "541512"
        rfp.triage_score = 0.85
        rfp.overall_score = 0.80
        return rfp

    def test_keyword_match_in_title(self, sample_rfp_obj):
        """Test keyword matching in title."""
        rule = MagicMock()
        rule.alert_type = AlertType.KEYWORD_MATCH
        rule.criteria = {
            "keywords": ["cloud"],
            "match_title": True,
            "match_description": False
        }

        assert _matches_criteria(sample_rfp_obj, rule) is True

    def test_keyword_match_in_description(self, sample_rfp_obj):
        """Test keyword matching in description."""
        rule = MagicMock()
        rule.alert_type = AlertType.KEYWORD_MATCH
        rule.criteria = {
            "keywords": ["cybersecurity"],
            "match_title": False,
            "match_description": True
        }

        assert _matches_criteria(sample_rfp_obj, rule) is True

    def test_keyword_no_match(self, sample_rfp_obj):
        """Test keyword not matching."""
        rule = MagicMock()
        rule.alert_type = AlertType.KEYWORD_MATCH
        rule.criteria = {
            "keywords": ["blockchain"],
            "match_title": True,
            "match_description": True
        }

        assert _matches_criteria(sample_rfp_obj, rule) is False

    def test_agency_match(self, sample_rfp_obj):
        """Test agency matching."""
        rule = MagicMock()
        rule.alert_type = AlertType.AGENCY_MATCH
        rule.criteria = {"agencies": ["Department of Defense", "NASA"]}

        assert _matches_criteria(sample_rfp_obj, rule) is True

    def test_agency_no_match(self, sample_rfp_obj):
        """Test agency not matching."""
        rule = MagicMock()
        rule.alert_type = AlertType.AGENCY_MATCH
        rule.criteria = {"agencies": ["NASA", "EPA"]}

        assert _matches_criteria(sample_rfp_obj, rule) is False

    def test_naics_match(self, sample_rfp_obj):
        """Test NAICS code matching."""
        rule = MagicMock()
        rule.alert_type = AlertType.NAICS_MATCH
        rule.criteria = {"naics_codes": ["541512", "541519"]}

        assert _matches_criteria(sample_rfp_obj, rule) is True

    def test_score_threshold_pass(self, sample_rfp_obj):
        """Test score threshold passing."""
        rule = MagicMock()
        rule.alert_type = AlertType.SCORE_THRESHOLD
        rule.criteria = {"min_score": 0.75, "score_type": "triage"}

        assert _matches_criteria(sample_rfp_obj, rule) is True

    def test_score_threshold_fail(self, sample_rfp_obj):
        """Test score threshold failing."""
        rule = MagicMock()
        rule.alert_type = AlertType.SCORE_THRESHOLD
        rule.criteria = {"min_score": 0.90, "score_type": "triage"}

        assert _matches_criteria(sample_rfp_obj, rule) is False


class TestFindMatchingRfps:
    """Tests for finding matching RFPs."""

    def test_find_keyword_matches(self, db_session, sample_rfp_list, sample_alert_rule):
        """Test finding RFPs by keyword."""
        # sample_alert_rule has keywords ["cybersecurity", "cloud", "IT"]
        # sample_rfp_list has "cloud and cybersecurity" in description

        matches = _find_matching_rfps(db_session, sample_alert_rule)

        assert len(matches) > 0

    def test_find_deadline_approaching(self, db_session, sample_rfp_list):
        """Test finding RFPs with approaching deadlines."""
        rule = AlertRule(
            name="Deadline Rule",
            alert_type=AlertType.DEADLINE_APPROACHING,
            priority=AlertPriority.HIGH,
            criteria={"days_before": 15},
            notification_channels=["in_app"],
        )
        db_session.add(rule)
        db_session.commit()

        matches = _find_matching_rfps(db_session, rule)

        # All sample RFPs have deadlines within 15 days
        assert len(matches) > 0

    def test_find_score_threshold(self, db_session, sample_rfp_list):
        """Test finding RFPs above score threshold."""
        rule = AlertRule(
            name="Score Rule",
            alert_type=AlertType.SCORE_THRESHOLD,
            priority=AlertPriority.URGENT,
            criteria={"min_score": 0.7, "score_type": "triage"},
            notification_channels=["in_app"],
        )
        db_session.add(rule)
        db_session.commit()

        matches = _find_matching_rfps(db_session, rule)

        # Check all matches have score >= 0.7
        for match in matches:
            assert match.triage_score >= 0.7


class TestBuildNotificationContent:
    """Tests for notification content building."""

    @pytest.fixture
    def sample_rfp_obj(self):
        """Create sample RFP for notifications."""
        rfp = MagicMock()
        rfp.rfp_id = "RFP-2024-001"
        rfp.title = "IT Services Contract for Cloud Migration"
        rfp.agency = "Department of Defense"
        rfp.triage_score = 0.85
        rfp.current_stage = MagicMock()
        rfp.current_stage.value = "discovered"
        rfp.response_deadline = datetime.utcnow() + timedelta(days=7)
        rfp.naics_code = "541512"
        return rfp

    def test_build_title_keyword_match(self, sample_rfp_obj):
        """Test title for keyword match alert."""
        rule = MagicMock()
        rule.alert_type = AlertType.KEYWORD_MATCH

        title = _build_notification_title(rule, sample_rfp_obj)

        assert "Keyword Match" in title
        assert "IT Services" in title

    def test_build_title_deadline_approaching(self, sample_rfp_obj):
        """Test title for deadline alert."""
        rule = MagicMock()
        rule.alert_type = AlertType.DEADLINE_APPROACHING

        title = _build_notification_title(rule, sample_rfp_obj)

        assert "Deadline" in title

    def test_build_title_score_threshold(self, sample_rfp_obj):
        """Test title for score threshold alert."""
        rule = MagicMock()
        rule.alert_type = AlertType.SCORE_THRESHOLD

        title = _build_notification_title(rule, sample_rfp_obj)

        assert "Score" in title or "85%" in title

    def test_build_message_deadline(self, sample_rfp_obj):
        """Test message for deadline alert."""
        rule = MagicMock()
        rule.alert_type = AlertType.DEADLINE_APPROACHING
        rule.name = "Deadline Rule"

        message = _build_notification_message(rule, sample_rfp_obj)

        assert "days" in message.lower()
        assert "Department of Defense" in message

    def test_build_message_keyword_match(self, sample_rfp_obj):
        """Test message for keyword match alert."""
        rule = MagicMock()
        rule.alert_type = AlertType.KEYWORD_MATCH
        rule.criteria = {"keywords": ["cloud", "IT"]}
        rule.name = "Keyword Rule"

        message = _build_notification_message(rule, sample_rfp_obj)

        assert "cloud" in message.lower() or "IT" in message


class TestAlertRulesEndpoint:
    """Integration tests for alert rules endpoints."""

    def test_list_rules_empty(self, db_session):
        """Test listing rules when none exist."""
        from app.routes.alerts import list_alert_rules

        # Need to run async
        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            list_alert_rules(db_session, active_only=False, alert_type=None)
        )

        assert result["rules"] == []
        assert result["total"] == 0

    def test_create_rule(self, db_session):
        """Test creating a new rule."""
        from app.routes.alerts import create_alert_rule

        rule_data = AlertRuleCreate(
            name="New Test Rule",
            alert_type=AlertType.KEYWORD_MATCH,
            priority=AlertPriority.HIGH,
            criteria={"keywords": ["test"]},
        )

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            create_alert_rule(db_session, rule_data)
        )

        assert result["name"] == "New Test Rule"
        assert result["is_active"] is True
        assert "id" in result

    def test_get_rule(self, db_session, sample_alert_rule):
        """Test getting a specific rule."""
        from app.routes.alerts import get_alert_rule

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            get_alert_rule(db_session, sample_alert_rule.id)
        )

        assert result["id"] == sample_alert_rule.id
        assert result["name"] == sample_alert_rule.name

    def test_get_rule_not_found(self, db_session):
        """Test getting non-existent rule."""
        from app.routes.alerts import get_alert_rule
        from fastapi import HTTPException

        import asyncio
        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                get_alert_rule(db_session, 99999)
            )
        assert exc_info.value.status_code == 404

    def test_update_rule(self, db_session, sample_alert_rule):
        """Test updating a rule."""
        from app.routes.alerts import update_alert_rule

        update_data = AlertRuleUpdate(name="Updated Name", is_active=False)

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            update_alert_rule(db_session, sample_alert_rule.id, update_data)
        )

        assert result["name"] == "Updated Name"
        assert result["is_active"] is False

    def test_delete_rule(self, db_session, sample_alert_rule):
        """Test deleting a rule."""
        from app.routes.alerts import delete_alert_rule

        rule_id = sample_alert_rule.id

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            delete_alert_rule(db_session, rule_id)
        )

        assert "deleted" in result["message"].lower()

        # Verify rule is gone
        deleted_rule = db_session.query(AlertRule).filter(
            AlertRule.id == rule_id
        ).first()
        assert deleted_rule is None

    def test_toggle_rule(self, db_session, sample_alert_rule):
        """Test toggling rule active status."""
        from app.routes.alerts import toggle_alert_rule

        original_status = sample_alert_rule.is_active

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            toggle_alert_rule(db_session, sample_alert_rule.id)
        )

        assert result["is_active"] == (not original_status)


class TestNotificationsEndpoint:
    """Tests for notification endpoints."""

    def test_list_notifications_empty(self, db_session):
        """Test listing notifications when none exist."""
        from app.routes.alerts import list_notifications

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            list_notifications(db_session, unread_only=False, priority=None, limit=50, offset=0)
        )

        assert result["notifications"] == []
        assert result["unread_count"] == 0

    def test_list_notifications_with_data(self, db_session, sample_notification):
        """Test listing notifications."""
        from app.routes.alerts import list_notifications

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            list_notifications(db_session, unread_only=False, priority=None, limit=50, offset=0)
        )

        assert len(result["notifications"]) == 1
        assert result["unread_count"] == 1

    def test_list_notifications_unread_only(self, db_session, sample_notification):
        """Test filtering unread notifications."""
        from app.routes.alerts import list_notifications

        # Mark as read
        sample_notification.is_read = True
        db_session.commit()

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            list_notifications(db_session, unread_only=True, priority=None, limit=50, offset=0)
        )

        assert len(result["notifications"]) == 0

    def test_notification_count(self, db_session, sample_notification):
        """Test notification count endpoint."""
        from app.routes.alerts import get_notification_count

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            get_notification_count(db_session)
        )

        assert result["unread"] == 1
        assert result["by_priority"]["high"] == 1

    def test_action_mark_read(self, db_session, sample_notification):
        """Test marking notification as read."""
        from app.routes.alerts import action_notification

        action = NotificationAction(action="mark_read")

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            action_notification(db_session, sample_notification.id, action)
        )

        assert result["is_read"] is True
        assert result["read_at"] is not None

    def test_action_dismiss(self, db_session, sample_notification):
        """Test dismissing notification."""
        from app.routes.alerts import action_notification

        action = NotificationAction(action="dismiss")

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            action_notification(db_session, sample_notification.id, action)
        )

        assert result["is_dismissed"] is True

    def test_mark_all_read(self, db_session, sample_alert_rule, sample_rfp):
        """Test marking all notifications as read."""
        # Create multiple unread notifications
        for i in range(3):
            notification = AlertNotification(
                rule_id=sample_alert_rule.id,
                rfp_id=sample_rfp.id,
                title=f"Test {i}",
                message="Test",
                priority=AlertPriority.MEDIUM,
                is_read=False,
            )
            db_session.add(notification)
        db_session.commit()

        from app.routes.alerts import mark_all_notifications_read

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            mark_all_notifications_read(db_session)
        )

        assert result["marked_read"] == 3


class TestAlertTypesEndpoint:
    """Tests for alert types info endpoint."""

    def test_list_alert_types(self):
        """Test listing available alert types."""
        from app.routes.alerts import list_alert_types

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(list_alert_types())

        assert "alert_types" in result
        assert "priorities" in result
        assert "notification_channels" in result

        # Check all AlertType values are documented
        for alert_type in AlertType:
            assert alert_type.value in result["alert_types"]

        # Check each type has required fields
        for type_name, type_info in result["alert_types"].items():
            assert "name" in type_info
            assert "description" in type_info
            assert "criteria_schema" in type_info


class TestEvaluateAlerts:
    """Tests for alert evaluation endpoint."""

    def test_evaluate_no_active_rules(self, db_session):
        """Test evaluation with no active rules."""
        from app.routes.alerts import evaluate_alerts

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            evaluate_alerts(db_session, rfp_id=None)
        )

        assert result["notifications_created"] == 0

    def test_evaluate_creates_notifications(self, db_session, sample_alert_rule, sample_rfp_list):
        """Test evaluation creates notifications for matches."""
        from app.routes.alerts import evaluate_alerts

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            evaluate_alerts(db_session, rfp_id=None)
        )

        # Should create notifications for matching RFPs
        assert result["rules_evaluated"] >= 1

    def test_evaluate_specific_rfp(self, db_session, sample_alert_rule, sample_rfp):
        """Test evaluation for specific RFP."""
        from app.routes.alerts import evaluate_alerts

        import asyncio
        result = asyncio.get_event_loop().run_until_complete(
            evaluate_alerts(db_session, rfp_id=sample_rfp.rfp_id)
        )

        assert result["rules_evaluated"] >= 1
