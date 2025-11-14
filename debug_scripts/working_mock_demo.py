"""
Working demonstration of mock LLM functionality
"""
import sys
import os
sys.path.append('/app/government_rfp_bid_1927/src')
def demo_working_mock():
    """Demonstrate working mock LLM"""
    print("=== Working Mock LLM Demo ===\n")
    try:
        from config.llm_config import LLMManager, LLMConfig
        # Create explicit mock configuration
        config = LLMConfig(
            provider="mock",
            model_name="mock-gpt-4-turbo", 
            use_mock=True
        )
        print("1. Creating Mock LLM Manager...")
        manager = LLMManager(config)
        print(f"   Manager available: {manager.is_available}")
        print(f"   Provider: {manager.config.provider}")
        if not manager.is_available:
            print("❌ Mock manager not available")
            return False
        print("\n2. Testing Mock Connection...")
        test_result = manager.test_connection()
        if test_result["success"]:
            print("✅ Connection successful!")
            print(f"   Response: {test_result['response']}")
            print(f"   Latency: {test_result['latency_seconds']:.3f}s")
        else:
            print(f"❌ Connection failed: {test_result['error']}")
            return False
        print("\n3. Testing Text Generation...")
        # Test different types of generation
        test_cases = [
            ("Executive Summary", "Write a brief executive summary for water delivery service"),
            ("Requirements Extraction", "Extract requirements: Need 500 bottles weekly for 6 months"),
            ("Pricing Analysis", "Calculate pricing for water service with 40% margin")
        ]
        for test_name, prompt in test_cases:
            try:
                result = manager.generate_text(prompt, max_tokens=100)
                print(f"   {test_name}: ✅ SUCCESS")
                print(f"      Preview: {result['text'][:60]}...")
            except Exception as e:
                print(f"   {test_name}: ❌ FAILED - {e}")
                return False
        print("\n✅ All mock tests passed!")
        print("✅ LLM infrastructure ready for development")
        return True
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = demo_working_mock()
    if success:
        print("\n🎉 Mock LLM infrastructure fully functional!")
    else:
        print("\n💥 Mock LLM demo failed")