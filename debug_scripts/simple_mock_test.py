"""
Simple test to verify mock LLM functionality
"""
import sys

sys.path.append('/app/government_rfp_bid_1927/src')
from config.llm_config import get_default_llm_manager


def test_simple_mock():
    """Simple test of mock functionality"""
    print("=== Simple Mock LLM Test ===")
    # Get default manager (should auto-fallback to mock)
    manager = get_default_llm_manager()
    print(f"Provider: {manager.config.provider}")
    print(f"Available: {manager.is_available}")
    if manager.is_available:
        # Test connection
        test_result = manager.test_connection()
        print(f"Connection test: {'✅ SUCCESS' if test_result['success'] else '❌ FAILED'}")
        if test_result['success']:
            print(f"Response: {test_result['response']}")
            print("✅ Mock LLM working correctly!")
            return True
    print("❌ Mock LLM not working")
    return False
if __name__ == "__main__":
    success = test_simple_mock()
    print(f"\nResult: {'SUCCESS' if success else 'FAILED'}")
