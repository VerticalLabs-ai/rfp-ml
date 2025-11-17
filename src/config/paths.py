"""
Path configuration for the RFP ML system.
Provides dynamic path resolution for local and Docker environments.
"""
import os
from pathlib import Path


def get_project_root():
    """
    Get the project root directory dynamically.
    Works in both local and Docker environments.
    """
    # Start from this file's location
    current_file = Path(__file__).resolve()

    # Navigate up to project root (2 levels up from src/config/)
    project_root = current_file.parent.parent.parent

    # Validate it's the correct directory by checking for key files
    if (project_root / "requirements.txt").exists():
        return project_root

    # Fallback to Docker path if local detection fails
    docker_path = Path("/app/government_rfp_bid_1927")
    if docker_path.exists():
        return docker_path

    # Last resort: use current file's grandparent
    return project_root


class PathConfig:
    """Centralized path configuration for the RFP ML system."""

    # Project root
    PROJECT_ROOT = get_project_root()

    # Source directories
    SRC_DIR = PROJECT_ROOT / "src"

    # Data directories
    DATA_DIR = PROJECT_ROOT / "data"
    RAW_DATA_DIR = DATA_DIR / "raw"
    PROCESSED_DATA_DIR = DATA_DIR / "processed"
    EMBEDDINGS_DIR = DATA_DIR / "embeddings"

    # Output directories
    OUTPUT_DIR = PROJECT_ROOT / "output"
    BID_DOCUMENTS_DIR = DATA_DIR / "bid_documents"
    COMPLIANCE_DIR = DATA_DIR / "compliance"
    PRICING_DIR = DATA_DIR / "pricing"
    TEMPLATES_DIR = DATA_DIR / "templates"
    CONTENT_LIBRARY_DIR = DATA_DIR / "content_library"

    # Test directories
    TESTS_DIR = PROJECT_ROOT / "tests"

    # Lazy initialization flag
    _initialized = False

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all necessary directories if they don't exist (lazy initialization)."""
        if cls._initialized:
            return

        directories = [
            cls.DATA_DIR,
            cls.RAW_DATA_DIR,
            cls.PROCESSED_DATA_DIR,
            cls.EMBEDDINGS_DIR,
            cls.OUTPUT_DIR,
            cls.BID_DOCUMENTS_DIR,
            cls.COMPLIANCE_DIR,
            cls.PRICING_DIR,
            cls.TEMPLATES_DIR,
            cls.CONTENT_LIBRARY_DIR,
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

        cls._initialized = True

    @classmethod
    def get_path(cls, *path_parts: str) -> Path:
        """
        Get a path relative to project root.

        Args:
            *path_parts: Path components to join

        Returns:
            Path object
        """
        cls.ensure_directories()
        return cls.PROJECT_ROOT.joinpath(*path_parts)

    @classmethod
    def get_data_path(cls, *path_parts: str) -> Path:
        """Get a path relative to data directory."""
        cls.ensure_directories()
        return cls.DATA_DIR.joinpath(*path_parts)

    @classmethod
    def get_output_path(cls, *path_parts: str) -> Path:
        """Get a path relative to output directory."""
        cls.ensure_directories()
        return cls.OUTPUT_DIR.joinpath(*path_parts)


# Convenience function for backward compatibility
def get_base_path():
    """Get the base project path as a string (for backward compatibility)."""
    return str(PathConfig.PROJECT_ROOT)


# Export commonly used paths as strings for convenience
# Note: Directories are created lazily on first access
BASE_PATH = str(PathConfig.PROJECT_ROOT)
DATA_PATH = str(PathConfig.DATA_DIR)
SRC_PATH = str(PathConfig.SRC_DIR)
