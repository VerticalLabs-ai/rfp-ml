"""
Configuration module for paths, logging, and application settings.
"""

from .paths import PathConfig, get_base_path, get_project_root
from .settings import DecisionSettings, RAGSettings, Settings, settings

try:
    from .logging_config import get_logger, setup_logging

    _HAS_LOGGING = True
    # Re-export for external use
    __get_logger = get_logger
    __setup_logging = setup_logging
except ImportError:
    _HAS_LOGGING = False

__all__ = [
    "PathConfig",
    "get_project_root",
    "get_base_path",
    "settings",
    "Settings",
    "DecisionSettings",
    "RAGSettings",
]

if _HAS_LOGGING:
    __all__.extend(["setup_logging", "get_logger"])
