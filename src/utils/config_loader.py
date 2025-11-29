"""
Configuration loading utilities.
Provides consistent config file loading with defaults across modules.
"""
import json
import logging
from pathlib import Path
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=dict[str, Any])


def load_or_create_config(
    path: str | Path,
    defaults: dict[str, Any],
    create_if_missing: bool = True
) -> dict[str, Any]:
    """
    Load configuration from a JSON file, or create it with defaults if missing.

    Args:
        path: Path to the configuration file
        defaults: Default configuration values
        create_if_missing: If True, create the file with defaults if it doesn't exist

    Returns:
        Loaded or default configuration dictionary

    Examples:
        >>> config = load_or_create_config(
        ...     "config/settings.json",
        ...     {"timeout": 30, "retries": 3}
        ... )
    """
    path = Path(path)

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                loaded = json.load(f)
            logger.info(f"Loaded configuration from {path}")
            # Merge with defaults to ensure all keys exist
            return {**defaults, **loaded}
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {path}: {e}, using defaults")
        except OSError as e:
            logger.warning(f"Failed to read {path}: {e}, using defaults")

    # File doesn't exist or failed to load
    if create_if_missing:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(defaults, f, indent=2)
            logger.info(f"Created default configuration at {path}")
        except OSError as e:
            logger.warning(f"Failed to create config file {path}: {e}")

    return defaults.copy()


def save_config(path: str | Path, config: dict[str, Any]) -> bool:
    """
    Save configuration to a JSON file.

    Args:
        path: Path to save the configuration
        config: Configuration dictionary to save

    Returns:
        True if successful, False otherwise
    """
    path = Path(path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Saved configuration to {path}")
        return True
    except OSError as e:
        logger.error(f"Failed to save config to {path}: {e}")
        return False
