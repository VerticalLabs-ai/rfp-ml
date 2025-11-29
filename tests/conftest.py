import os
import sys
from unittest.mock import MagicMock

import pytest

# Ensure src is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pricing.pricing_engine import PricingEngine


@pytest.fixture
def mock_llm():
    """Fixture for a mock LLM to avoid API calls during tests."""
    mock = MagicMock()
    mock.generate.return_value = "Mocked LLM response"
    return mock

@pytest.fixture
def pricing_engine():
    """Fixture for the PricingEngine."""
    engine = PricingEngine()
    # Mock internal components if necessary to avoid external dependencies
    # For now, we assume PricingEngine can run with default initialization
    # or we might need to mock its dependencies if it calls LLMs/DBs directly.
    return engine
