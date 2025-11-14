"""
Test script for LLM configuration validation
Tests both OpenAI API and local model functionality
"""
import sys
import os
import time
sys.path.append('/app/government_rfp_bid_1927')
from src.config.llm_config import LLMManager, LLMConfig
def test_llm_infrastructure():
    """Comprehensive test of LLM infrastructure"""
    print("=" * 60)
    print("LLM Infrastructure Validation Test")
    print("=" * 60)
    # Create optimized config for CPU environment
    config = LLMConfig(
        # Use a smaller, more efficient local model for testing
        local_model_name="distilgpt2",  # Smaller model for faster testing
        local_model_temperature=0.7,
        local_model_max_tokens=512,
        use_gpu=False,  # Force CPU usage
        max_retry_attempts=2,
        request_timeout=30
    )
    try:
        # Initialize LLM manager
        print("1. Initializing LLM Manager...")
        llm_manager = LLMManager(config)
        print("   ✓ LLM Manager initialized successfully")
        # Get model information
        print("\n2. Model Information:")
        model_info = llm_manager.get_model_info()
        for key, value in model_info.items():
            print(f"   {key}: {value}")
        # Validate setup
        print("\n3. Validating Setup...")
        start_time = time.time()
        validation_results = llm_manager.validate_setup()
        validation_time = time.time() - start_time
        print(f"   Setup validation time: {validation_time:.2f}s")
        print(f"   Setup valid: {validation_results['setup_valid']}")
        print(f"   OpenAI status: {validation_results['openai_status']}")
        print(f"   Local model status: {validation_results['local_model_status']}")
        if validation_results['performance_metrics']:
            metrics = validation_results['performance_metrics']
            print(f"   Generation time: {metrics.get('generation_time', 'N/A'):.2f}s")
            print(f"   Response length: {metrics.get('response_length', 'N/A')} chars")
        if validation_results['errors']:
            print("   Errors:")
            for error in validation_results['errors']:
                print(f"     - {error}")
        # Test different generation tasks
        if validation_results['setup_valid']:
            print("\n4. Testing Different Generation Tasks...")
            # Test 1: General generation
            print("   Test 1: General text generation")
            try:
                response = llm_manager.generate_text(
                    "What are the key components of a government bid proposal?",
                    task_type="general",
                    max_tokens=100
                )
                print(f"     ✓ Response length: {len(response)} chars")
                print(f"     Preview: {response[:100]}...")
            except Exception as e:
                print(f"     ✗ Failed: {e}")
            # Test 2: Structured extraction
            print("   Test 2: Structured extraction task")
            try:
                prompt = """
                Extract key requirements from this RFP excerpt:
                "The contractor must provide bottled water delivery service for 12 months.
                Delivery must occur bi-weekly. All water must meet FDA standards."
                Format as JSON with keys: duration, frequency, standards.
                """
                response = llm_manager.generate_text(
                    prompt,
                    task_type="structured_extraction",
                    max_tokens=150
                )
                print(f"     ✓ Response length: {len(response)} chars")
                print(f"     Preview: {response[:100]}...")
            except Exception as e:
                print(f"     ✗ Failed: {e}")
            # Test 3: Bid generation
            print("   Test 3: Bid generation task")
            try:
                prompt = """
                Write a brief company qualifications section for a water delivery service bid.
                Company: AquaServe Solutions
                Experience: 10 years in commercial water delivery
                Certifications: FDA approved, ISO 9001
                Keep response under 100 words.
                """
                response = llm_manager.generate_text(
                    prompt,
                    task_type="bid_generation",
                    max_tokens=150
                )
                print(f"     ✓ Response length: {len(response)} chars")
                print(f"     Preview: {response[:100]}...")
            except Exception as e:
                print(f"     ✗ Failed: {e}")
        else:
            print("\n4. Skipping generation tests - setup validation failed")
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        if validation_results['setup_valid']:
            print("✓ LLM infrastructure is operational")
            primary_backend = "OpenAI API" if validation_results['openai_status'] == 'operational' else "Local Model"
            print(f"✓ Primary backend: {primary_backend}")
            print("✓ Ready for bid generation pipeline integration")
        else:
            print("✗ LLM infrastructure has issues")
            print("  Check errors above and resolve before proceeding")
        return validation_results['setup_valid']
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = test_llm_infrastructure()
    sys.exit(0 if success else 1)