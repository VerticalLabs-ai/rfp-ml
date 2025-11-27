import pytest
import os
from unittest.mock import patch, MagicMock
from src.config.llm_config import LLMManager, LLMConfigManager, LLMProvider, LLMConfig

class TestLLMConfig:
    """Test script for LLM configuration validation"""

    @pytest.fixture
    def config_manager(self):
        """Fixture for LLM Config Manager."""
        return LLMConfigManager()

    @pytest.fixture
    def llm_manager(self):
        """Fixture for LLM Manager."""
        return LLMManager()

    def test_config_initialization(self, config_manager):
        """Test that LLM Config Manager initializes correctly."""
        assert config_manager is not None
        assert config_manager.config is not None
        assert isinstance(config_manager.config.provider, LLMProvider)

    def test_validate_setup(self, llm_manager):
        """Test setup validation."""
        validation_results = llm_manager.validate_setup()
        assert validation_results is not None
        assert "setup_valid" in validation_results
        assert "status" in validation_results
        assert "provider" in validation_results

    def test_get_config(self, config_manager):
        """Test getting config with task overrides."""
        config = config_manager.get_config("bid_generation")
        assert config is not None
        assert config.temperature == 0.7
        
        config_pricing = config_manager.get_config("pricing_calculation")
        assert config_pricing.temperature == 0.2

    @pytest.mark.skip(reason="Requires active LLM connection/model download which might be slow or fail in CI")
    def test_generation_tasks(self, llm_manager):
        """Test actual generation tasks."""
        if not llm_manager.validate_setup()['setup_valid']:
            pytest.skip("LLM setup not valid")

        # Test 1: General generation
        response = llm_manager.generate_text(
            "What are the key components of a government bid proposal?",
            task_type="bid_generation",
            max_tokens=100
        )
        # Response might be empty string if failure, but should not raise
        assert isinstance(response, str)