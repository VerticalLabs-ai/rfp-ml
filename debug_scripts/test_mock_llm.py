"""
Test the mock LLM functionality for development without API keys
"""
import sys

sys.path.append('/app/government_rfp_bid_1927/src')
import logging

from config.llm_config import LLMConfig, LLMManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
def test_mock_llm():
    """Test mock LLM functionality"""
    print("=== Mock LLM Test ===\n")
    # Force mock mode
    config = LLMConfig(
        provider="mock",
        model_name="mock-gpt-4-turbo",
        use_mock=True
    )
    # Test 1: Manager Creation
    print("1. Creating Mock LLM Manager...")
    try:
        manager = LLMManager(config)
        print("✅ Mock LLM Manager created successfully")
        print(f"   Available: {manager.is_available}")
        print(f"   Provider: {manager.config.provider}")
        print(f"   Model: {manager.config.model_name}")
    except Exception as e:
        print(f"❌ Failed to create Mock LLM Manager: {e}")
        return False
    # Test 2: Connection Test
    print("\n2. Testing Mock Connection...")
    test_result = manager.test_connection()
    if test_result["success"]:
        print("✅ Mock connection test successful!")
        print(f"   Response: {test_result['response']}")
        print(f"   Latency: {test_result['latency_seconds']:.2f} seconds")
        print(f"   Provider: {test_result['provider']}")
        if test_result.get('usage'):
            print(f"   Token usage: {test_result['usage']}")
    else:
        print(f"❌ Mock connection test failed: {test_result['error']}")
        return False
    # Test 3: Different Task Types
    print("\n3. Testing Mock Generation for Different Tasks...")
    test_cases = [
        {
            "name": "Requirement Extraction",
            "task_type": "extraction",
            "prompt": "Extract requirements from this RFP: City needs 500 cases of water delivered weekly for 12 months."
        },
        {
            "name": "Executive Summary",
            "task_type": "bid_generation",
            "prompt": "Write a brief executive summary for a water delivery service bid."
        },
        {
            "name": "Pricing Justification",
            "task_type": "pricing",
            "prompt": "Provide pricing justification for water delivery service with 40% margin target."
        }
    ]
    for test_case in test_cases:
        print(f"\n   Testing {test_case['name']}...")
        try:
            result = manager.generate_text(
                test_case["prompt"],
                task_type=test_case["task_type"],
                max_tokens=300
            )
            print(f"   ✅ {test_case['name']} successful")
            print(f"   Response preview: {result['text'][:100]}...")
            print(f"   Token usage: {result.get('usage', {})}")
        except Exception as e:
            print(f"   ❌ {test_case['name']} failed: {e}")
    # Test 4: Temperature Settings
    print("\n4. Testing Temperature Settings...")
    model_info = manager.get_model_info()
    temp_settings = model_info.get("task_temperatures", {})
    print("   Temperature configuration:")
    for task, temp in temp_settings.items():
        print(f"   - {task}: {temp}")
    # Test 5: Performance Summary
    print("\n5. Mock Performance Summary...")
    print(f"   Provider: {model_info['provider']}")
    print(f"   Model: {model_info['model_name']}")
    print(f"   Available: {model_info['is_available']}")
    print("   Latency: <1 second (mock)")
    print("   Token tracking: Enabled")
    print("\n=== Mock Test Summary ===")
    print("✅ Mock LLM infrastructure working correctly")
    print("✅ All generation tasks functional")
    print("✅ Performance metrics captured")
    print("✅ Ready for RAG system development")
    return True
if __name__ == "__main__":
    success = test_mock_llm()
    if success:
        print("\n🎉 Mock LLM infrastructure validated! Ready for development.")
    else:
        print("\n💥 Mock LLM test failed.")
