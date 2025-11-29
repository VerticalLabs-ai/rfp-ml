"""
LLM Adapter - Provides unified interface for both full and minimal LLM configurations
"""
import logging
from typing import Any


def get_llm_manager(prefer_full: bool = True):
    """
    Get the best available LLM manager based on system capabilities
    Args:
        prefer_full: Whether to prefer the full LLM config if available
    Returns:
        LLM Manager instance (either full or minimal)
    """
    if prefer_full:
        try:
            # Try the full configuration first
            from .llm_config import create_llm_manager
            manager = create_llm_manager()
            logging.info("Using full LLM configuration")
            return manager
        except Exception as e:
            logging.warning(f"Full LLM config failed: {str(e)}, falling back to minimal")
    # Use minimal configuration
    try:
        from .minimal_llm_config import create_minimal_llm_manager
        manager = create_minimal_llm_manager()
        logging.info("Using minimal LLM configuration")
        return manager
    except Exception as e:
        logging.error(f"Both LLM configurations failed: {str(e)}")
        raise RuntimeError("No LLM configuration available") from e
class UnifiedLLMInterface:
    """
    Unified interface that works with both full and minimal LLM managers
    """
    def __init__(self, prefer_full: bool = True):
        """Initialize with best available LLM manager"""
        self.manager = get_llm_manager(prefer_full)
        self.logger = logging.getLogger(__name__)
    def generate_text(
        self,
        prompt: str,
        use_case: str = "bid_generation",
        **kwargs
    ) -> dict[str, Any]:
        """Generate text using the underlying manager"""
        return self.manager.generate_text(prompt, use_case, **kwargs)
    def test_connection(self) -> dict[str, Any]:
        """Test the connection"""
        return self.manager.test_connection()
    def get_status(self) -> dict[str, Any]:
        """Get manager status"""
        status = self.manager.get_status()
        # Add adapter info
        status["adapter_type"] = type(self.manager).__name__
        return status
    def is_openai_available(self) -> bool:
        """Check if OpenAI is available"""
        status = self.get_status()
        return status.get("openai_available", False)
    def is_production_ready(self) -> bool:
        """Check if the setup is production ready"""
        try:
            test_result = self.test_connection()
            return test_result["status"] == "success"
        except Exception:
            return False
def create_llm_interface(prefer_full: bool = True) -> UnifiedLLMInterface:
    """Factory function to create unified LLM interface"""
    return UnifiedLLMInterface(prefer_full)
# For backward compatibility, provide the same interface as the original module
def create_llm_manager(config_overrides: dict[str, Any] | None = None):
    """
    Backward compatible function that returns the best available LLM manager
    """
    try:
        # Try minimal config first as it's more stable
        from .minimal_llm_config import create_minimal_llm_manager
        return create_minimal_llm_manager(config_overrides)
    except Exception as err:
        # If that fails, there's a serious problem
        raise RuntimeError("No LLM configuration available") from err
if __name__ == "__main__":
    print("=== LLM Adapter Test ===")
    try:
        # Test unified interface
        interface = create_llm_interface()
        status = interface.get_status()
        print(f"✓ Adapter type: {status['adapter_type']}")
        print(f"✓ Backend: {status['current_backend']}")
        print(f"✓ OpenAI available: {interface.is_openai_available()}")
        print(f"✓ Production ready: {interface.is_production_ready()}")
        # Test generation
        result = interface.generate_text("Test prompt", "bid_generation")
        print(f"✓ Generation working: {result['backend']}")
        print("✅ LLM Adapter working correctly!")
    except Exception as e:
        print(f"❌ Adapter test failed: {str(e)}")
