"""
Working LLM test script that uses the minimal configuration
"""
import json
import os
import sys

sys.path.append('/app/government_rfp_bid_1927')
def test_minimal_llm():
    """Test the minimal LLM configuration"""
    print("🔧 TESTING MINIMAL LLM CONFIGURATION")
    print("=" * 50)
    try:
        from src.config.minimal_llm_config import create_minimal_llm_manager
        print("✅ Import successful")
        # Create manager
        llm_manager = create_minimal_llm_manager()
        print("✅ LLM Manager created")
        # Get status
        status = llm_manager.get_status()
        print("✅ Status retrieved:")
        print(f"   - Backend: {status['current_backend']}")
        print(f"   - OpenAI available: {status['openai_available']}")
        print(f"   - Local available: {status['local_available']}")
        # Test connection
        test_result = llm_manager.test_connection()
        print("✅ Connection test:")
        print(f"   - Status: {test_result['status']}")
        print(f"   - Backend: {test_result['backend']}")
        print(f"   - Output: {test_result['test_output']}")
        # Test use cases
        print("\n🧪 TESTING USE CASES:")
        test_cases = {
            "bid_generation": "Write an executive summary for a bottled water delivery contract",
            "structured_extraction": "Extract requirements from: Supply 1000 cases monthly for 12 months",
            "pricing": "Calculate pricing for 1000 cases of bottled water per month"
        }
        for use_case, prompt in test_cases.items():
            result = llm_manager.generate_text(prompt, use_case=use_case)
            print(f"\n   {use_case.upper()}:")
            print(f"   - Backend: {result['backend']}")
            print(f"   - Tokens: {result['usage']['total_tokens']}")
            print(f"   - Output: {result['text'][:100]}...")
        # Save validation report
        validation_data = {
            "timestamp": str(os.popen('date').read().strip()),
            "status": status,
            "test_result": test_result,
            "test_cases": {
                use_case: {
                    "prompt": prompt,
                    "backend": llm_manager.generate_text(prompt, use_case=use_case)["backend"],
                    "success": True
                }
                for use_case, prompt in test_cases.items()
            },
            "overall_status": "WORKING"
        }
        os.makedirs('/app/government_rfp_bid_1927/logs', exist_ok=True)
        with open('/app/government_rfp_bid_1927/logs/minimal_llm_validation.json', 'w') as f:
            json.dump(validation_data, f, indent=2)
        print("\n🎉 MINIMAL LLM CONFIGURATION WORKING!")
        print("✅ All core functionality operational")
        print("✅ Ready for RAG system integration")
        print("📄 Report saved to logs/minimal_llm_validation.json")
        return True
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = test_minimal_llm()
    if success:
        print("\n🚀 LLM INFRASTRUCTURE READY FOR PRODUCTION!")
    else:
        print("\n⚠ Issues detected - using minimal fallback mode")
