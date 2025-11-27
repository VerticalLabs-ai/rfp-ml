"""
Configuration module for paths, logging, and application settings.
"""
from .paths import PathConfig, get_project_root, get_base_path
from .settings import settings, Settings, DecisionSettings, RAGSettings

try:
    from .logging_config import setup_logging, get_logger
    _HAS_LOGGING = True
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
