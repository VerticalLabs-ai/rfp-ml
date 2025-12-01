"""
Feature Flags System for progressive feature enablement.

Auto-detects configuration availability and provides feature toggle support
for streaming, job queues, email alerts, and other optional features.
"""
import os
from enum import Enum
from typing import Any

from app.core.config import settings


class FeatureFlag(str, Enum):
    """Available feature flags."""

    # Infrastructure features
    STREAMING_ENABLED = "streaming_enabled"
    CELERY_JOBS = "celery_jobs"
    WEBSOCKET_CHANNELS = "websocket_channels"

    # Alert features
    EMAIL_ALERTS = "email_alerts"
    SLACK_ALERTS = "slack_alerts"
    WEBHOOK_ALERTS = "webhook_alerts"

    # Chat features
    CHAT_PERSISTENCE = "chat_persistence"
    CHAT_STREAMING = "chat_streaming"

    # Search features
    NL_SEARCH = "nl_search"
    RAG_SEARCH = "rag_search"

    # Copilot features
    COPILOT_SIDEBAR = "copilot_sidebar"
    REALTIME_SCORING = "realtime_scoring"
    COMPLIANCE_VIEWER = "compliance_viewer"

    # Premium features
    CLAUDE_THINKING = "claude_thinking"
    CLAUDE_OPUS = "claude_opus"


class FeatureFlags:
    """
    Feature flag management with auto-detection.

    Flags are automatically enabled based on configuration availability:
    - CELERY_JOBS: Enabled if REDIS_URL is configured
    - EMAIL_ALERTS: Enabled if SMTP_HOST or SENDGRID_API_KEY is set
    - STREAMING_ENABLED: Enabled if ANTHROPIC_API_KEY is set
    - etc.

    Usage:
        from app.core.feature_flags import feature_flags

        if feature_flags.is_enabled(FeatureFlag.STREAMING_ENABLED):
            # Use streaming
        else:
            # Use fallback

        # Or check with string
        if feature_flags.is_enabled("streaming_enabled"):
            ...
    """

    def __init__(self):
        """Initialize feature flags with auto-detection."""
        self._flags: dict[str, bool] = {}
        self._overrides: dict[str, bool] = {}
        self._detect_features()

    def _detect_features(self):
        """Auto-detect feature availability based on configuration."""
        # Check for Anthropic API key
        anthropic_available = bool(os.getenv("ANTHROPIC_API_KEY"))

        # Check for Redis
        redis_available = bool(getattr(settings, "REDIS_URL", None))

        # Check for email configuration
        smtp_available = bool(getattr(settings, "SMTP_HOST", None))
        sendgrid_available = bool(os.getenv("SENDGRID_API_KEY"))
        email_available = smtp_available or sendgrid_available

        # Check for Slack
        slack_available = bool(getattr(settings, "SLACK_WEBHOOK_URL", None))

        # Set flags based on detection
        self._flags = {
            # Infrastructure
            FeatureFlag.STREAMING_ENABLED.value: anthropic_available,
            FeatureFlag.CELERY_JOBS.value: redis_available,
            FeatureFlag.WEBSOCKET_CHANNELS.value: True,  # Always available

            # Alerts
            FeatureFlag.EMAIL_ALERTS.value: email_available,
            FeatureFlag.SLACK_ALERTS.value: slack_available,
            FeatureFlag.WEBHOOK_ALERTS.value: True,  # Always available

            # Chat
            FeatureFlag.CHAT_PERSISTENCE.value: True,  # Database always available
            FeatureFlag.CHAT_STREAMING.value: anthropic_available,

            # Search
            FeatureFlag.NL_SEARCH.value: True,  # Always available
            FeatureFlag.RAG_SEARCH.value: self._check_rag_available(),

            # Copilot
            FeatureFlag.COPILOT_SIDEBAR.value: True,  # Always available
            FeatureFlag.REALTIME_SCORING.value: True,  # Always available
            FeatureFlag.COMPLIANCE_VIEWER.value: True,  # Always available

            # Premium
            FeatureFlag.CLAUDE_THINKING.value: anthropic_available,
            FeatureFlag.CLAUDE_OPUS.value: anthropic_available,
        }

    def _check_rag_available(self) -> bool:
        """Check if RAG index is built and available."""
        try:
            from pathlib import Path
            embeddings_dir = Path("data/embeddings")
            if embeddings_dir.exists():
                return (embeddings_dir / "faiss_index.bin").exists()
            return False
        except Exception:
            return False

    def is_enabled(self, flag: FeatureFlag | str) -> bool:
        """
        Check if a feature flag is enabled.

        Args:
            flag: Feature flag enum value or string name

        Returns:
            True if feature is enabled, False otherwise
        """
        flag_name = flag.value if isinstance(flag, FeatureFlag) else flag

        # Check overrides first
        if flag_name in self._overrides:
            return self._overrides[flag_name]

        return self._flags.get(flag_name, False)

    def set_override(self, flag: FeatureFlag | str, enabled: bool):
        """
        Override a feature flag (useful for testing or admin control).

        Args:
            flag: Feature flag to override
            enabled: New enabled state
        """
        flag_name = flag.value if isinstance(flag, FeatureFlag) else flag
        self._overrides[flag_name] = enabled

    def clear_override(self, flag: FeatureFlag | str):
        """Remove an override and return to auto-detected state."""
        flag_name = flag.value if isinstance(flag, FeatureFlag) else flag
        self._overrides.pop(flag_name, None)

    def clear_all_overrides(self):
        """Remove all overrides."""
        self._overrides.clear()

    def get_all_flags(self) -> dict[str, bool]:
        """Get all flag states (including overrides)."""
        result = self._flags.copy()
        result.update(self._overrides)
        return result

    def get_status(self) -> dict[str, Any]:
        """
        Get detailed status of all feature flags.

        Returns dict with:
        - flags: Current state of all flags
        - overrides: List of overridden flags
        - detection: Auto-detected values
        """
        return {
            "flags": self.get_all_flags(),
            "overrides": list(self._overrides.keys()),
            "detection": {
                "anthropic_configured": bool(os.getenv("ANTHROPIC_API_KEY")),
                "redis_configured": bool(getattr(settings, "REDIS_URL", None)),
                "smtp_configured": bool(getattr(settings, "SMTP_HOST", None)),
                "slack_configured": bool(getattr(settings, "SLACK_WEBHOOK_URL", None)),
                "rag_available": self._check_rag_available(),
            },
        }

    def refresh(self):
        """Re-detect features (call after configuration changes)."""
        self._detect_features()


# Singleton instance
feature_flags = FeatureFlags()


def require_feature(flag: FeatureFlag | str):
    """
    Decorator to require a feature flag for an endpoint.

    Usage:
        @router.get("/stream")
        @require_feature(FeatureFlag.STREAMING_ENABLED)
        async def stream_endpoint():
            ...
    """
    from functools import wraps
    from fastapi import HTTPException

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not feature_flags.is_enabled(flag):
                flag_name = flag.value if isinstance(flag, FeatureFlag) else flag
                raise HTTPException(
                    status_code=501,
                    detail=f"Feature '{flag_name}' is not enabled. Check your configuration."
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# Export convenience function
def is_feature_enabled(flag: FeatureFlag | str) -> bool:
    """Convenience function to check if a feature is enabled."""
    return feature_flags.is_enabled(flag)
