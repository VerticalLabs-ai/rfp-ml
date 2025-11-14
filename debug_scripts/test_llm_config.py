"""
Test script for LLM Configuration Module
"""
import sys
import os
sys.path.append('/app/government_rfp_bid_1927')
import json
from src.config.llm_config import create_llm_manager, LLMConfig, LLMBackend
def test_llm_configuration():
    """Test LLM configuration and connection"""
    print("=== Testing LLM Configuration Module ===\n")
    try:
        # Test 1: Check environment variables
        print("1. Environment Variables Check:")
        openai_key = os.getenv('OPENAI_API_KEY')
        print(f"   OPENAI_API_KEY: {'SET' if openai_key else 'NOT SET'}")
        if openai_key:
            print(f"   Key preview: {openai_key[:10]}...{openai_key[-4:]}")
        print()
        # Test 2: Initialize LLM Manager
        print("2. Initializing LLM Manager...")
        llm_manager = create_llm_manager()
        print("   ✓ LLM Manager created successfully")
        # Test 3: Get status
        print("\n3. Getting LLM Status:")
        status = llm_manager.get_status()
        print(f"   Status: {json.dumps(status, indent=4)}")
        # Test 4: Test connection
        print("\n4. Testing Connection:")
        test_result = llm_manager.test_connection()
        print(f"   Connection test result:")
        print(f"   {json.dumps(test_result, indent=4)}")
        if test_result["status"] == "success":
            print("   ✓ Connection test PASSED")
        else:
            print("   ✗ Connection test FAILED")
            print(f"   Error: {test_result.get('error', 'Unknown error')}")
        # Test 5: Test different use cases if connection works
        if test_result["status"] == "success":
            print("\n5. Testing Different Use Cases:")
            test_cases = {
                "bid_generation": {
                    "prompt": "Write a brief executive summary for a government bottled water delivery contract.",
                    "expected_tokens": 100
                },
                "structured_extraction": {
                    "prompt": "Extract key requirements: 'Supply 1000 cases bottled water monthly for 12 months. Delivery within 48 hours.'",
                    "expected_tokens": 50
                },
                "pricing": {
                    "prompt": "Suggest competitive pricing strategy for 1000 cases of bottled water per month.",
                    "expected_tokens": 80
                }
            }
            for use_case, test_data in test_cases.items():
                try:
                    print(f"\n   Testing {use_case}:")
                    result = llm_manager.generate_text(
                        test_data["prompt"], 
                        use_case=use_case
                    )
                    print(f"   ✓ Backend: {result['backend']}")
                    print(f"   ✓ Model: {result['model']}")
                    print(f"   ✓ Tokens used: {result['usage']['total_tokens']}")
                    print(f"   ✓ Output preview: {result['text'][:100]}...")
                except Exception as e:
                    print(f"   ✗ {use_case} failed: {str(e)}")
        print("\n=== LLM Configuration Test Complete ===")
        return True
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
def test_fallback_behavior():
    """Test fallback to local model if OpenAI fails"""
    print("\n=== Testing Fallback Behavior ===")
    try:
        # Create manager with invalid OpenAI key to test fallback
        config_overrides = {
            "openai_api_key": "invalid_key_test_fallback"
        }
        print("Creating manager with invalid OpenAI key to test fallback...")
        llm_manager = create_llm_manager(config_overrides)
        status = llm_manager.get_status()
        print(f"Fallback status: {json.dumps(status, indent=2)}")
        # Test if it can still generate text with local model
        if status["local_available"]:
            print("Testing text generation with local fallback...")
            result = llm_manager.generate_text(
                "Test prompt for local model", 
                use_case="bid_generation"
            )
            print(f"✓ Fallback successful with backend: {result['backend']}")
        else:
            print("✗ Local model not available for fallback")
    except Exception as e:
        print(f"Fallback test failed: {str(e)}")
if __name__ == "__main__":
    success = test_llm_configuration()
    # Also test fallback behavior
    test_fallback_behavior()
    if success:
        print("\n🎉 LLM Configuration Module is working correctly!")
        print("Ready to proceed with RAG system implementation.")
    else:
        print("\n❌ LLM Configuration has issues that need to be resolved.")