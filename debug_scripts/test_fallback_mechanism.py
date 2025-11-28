"""
Test the fallback mechanism when OpenAI API is not available
"""
import sys
import os
sys.path.append('/app/government_rfp_bid_1927/src')
from config.llm_config import LLMManager, LLMConfig
import logging
# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
def test_fallback_scenarios():
    """Test different fallback scenarios"""
    print("=== LLM Fallback Mechanism Test ===\n")
    # Scenario 1: No API key (should fail gracefully)
    print("1. Testing with no API key...")
    config_no_key = LLMConfig(
        provider="openai",
        api_key=None,
        model_name="gpt-5.1"
    )
    try:
        manager = LLMManager(config_no_key)
        print(f"   Manager created, available: {manager.is_available}")
        if not manager.is_available:
            print("   ✅ Correctly detected unavailable API")
        else:
            print("   ⚠️  Unexpected: Manager shows available without API key")
    except Exception as e:
        print(f"   ✅ Expected error caught: {e}")
    # Scenario 2: Invalid model name (should attempt fallback)
    print("\n2. Testing with invalid model name...")
    config_invalid_model = LLMConfig(
        provider="openai",
        api_key=os.getenv("OPENAI_API_KEY", "dummy_key"),
        model_name="invalid-model-name"
    )
    try:
        manager = LLMManager(config_invalid_model)
        print(f"   Manager created, available: {manager.is_available}")
        if manager.is_available:
            print(f"   ✅ Fallback successful, using: {manager.config.model_name}")
        else:
            print("   ⚠️  Fallback mechanism could not recover")
    except Exception as e:
        print(f"   Error during fallback test: {e}")
    # Scenario 3: Show configuration details
    print("\n3. Current environment configuration:")
    api_key_available = bool(os.getenv("OPENAI_API_KEY"))
    print(f"   OPENAI_API_KEY available: {api_key_available}")
    if api_key_available:
        api_key_preview = os.getenv("OPENAI_API_KEY")[:10] + "..." if os.getenv("OPENAI_API_KEY") else "None"
        print(f"   API Key preview: {api_key_preview}")
    env_vars = [
        "LLM_PROVIDER", "LLM_MODEL_NAME", "LLM_TEMPERATURE", 
        "LLM_MAX_TOKENS", "OPENAI_BASE_URL"
    ]
    for var in env_vars:
        value = os.getenv(var, "Not set")
        print(f"   {var}: {value}")
    print("\n=== Fallback Test Complete ===")
if __name__ == "__main__":
    test_fallback_scenarios()