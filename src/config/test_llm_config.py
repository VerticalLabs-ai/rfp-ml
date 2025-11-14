"""
Test script for LLM configuration validation
"""
import sys
import os
import json
import time
from typing import Dict, Any
# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config.llm_config import (
    LLMConfigManager, 
    LLMInterface, 
    LLMProvider,
    test_llm_connection,
    generate_completion
)
def test_configuration_initialization():
    """Test LLM configuration initialization"""
    print("=" * 50)
    print("Testing LLM Configuration Initialization")
    print("=" * 50)
    try:
        config_manager = LLMConfigManager()
        validation = config_manager.validate_configuration()
        print(f"Configuration Status: {validation['status']}")
        print(f"Provider: {validation['provider']}")
        print(f"Model: {validation['model']}")
        print(f"Has API Key: {validation['has_api_key']}")
        print(f"Configuration: {json.dumps(validation['configuration'], indent=2)}")
        return validation['status'] == 'success'
    except Exception as e:
        print(f"Configuration test failed: {e}")
        return False
def test_task_specific_configs():
    """Test task-specific configuration overrides"""
    print("\n" + "=" * 50)
    print("Testing Task-Specific Configurations")
    print("=" * 50)
    try:
        config_manager = LLMConfigManager()
        tasks = [
            "bid_generation",
            "requirement_extraction", 
            "pricing_calculation",
            "compliance_analysis",
            "go_nogo_decision"
        ]
        for task in tasks:
            config = config_manager.get_config(task)
            print(f"\nTask: {task}")
            print(f"  Temperature: {config.temperature}")
            print(f"  Max Tokens: {config.max_tokens}")
            print(f"  Model: {config.model_name}")
        return True
    except Exception as e:
        print(f"Task configuration test failed: {e}")
        return False
def test_llm_interface():
    """Test LLM interface with different task types"""
    print("\n" + "=" * 50)
    print("Testing LLM Interface")
    print("=" * 50)
    try:
        config_manager = LLMConfigManager()
        llm_interface = LLMInterface(config_manager)
        # Test different task types
        test_cases = [
            {
                "task": "bid_generation",
                "prompt": "Generate a brief executive summary for a bottled water delivery contract.",
                "system": "You are an expert bid writer for government contracts."
            },
            {
                "task": "requirement_extraction",
                "prompt": "Extract requirements from this RFP: 'Contractor must provide 500 cases of bottled water monthly.'",
                "system": "You are a requirements analysis expert."
            },
            {
                "task": "pricing_calculation",
                "prompt": "Calculate pricing for 500 cases of bottled water at $3 per case with 40% margin.",
                "system": "You are a pricing specialist."
            }
        ]
        for test_case in test_cases:
            print(f"\nTesting task: {test_case['task']}")
            start_time = time.time()
            response = llm_interface.generate_completion(
                prompt=test_case['prompt'],
                task_type=test_case['task'],
                system_message=test_case['system']
            )
            end_time = time.time()
            response_time = end_time - start_time
            print(f"  Status: {response['status']}")
            print(f"  Response Time: {response_time:.2f} seconds")
            print(f"  Content Preview: {response.get('content', 'N/A')[:100]}...")
            if response['status'] != 'success':
                print(f"  Error: {response.get('error', 'Unknown error')}")
        return True
    except Exception as e:
        print(f"LLM interface test failed: {e}")
        return False
def test_connection_validation():
    """Test connection validation"""
    print("\n" + "=" * 50)
    print("Testing Connection Validation")
    print("=" * 50)
    try:
        start_time = time.time()
        result = test_llm_connection()
        end_time = time.time()
        print(f"Connection Test Result: {result['status']}")
        print(f"Message: {result['message']}")
        print(f"Response Time: {end_time - start_time:.2f} seconds")
        if result['status'] == 'success':
            print(f"Test Response: {result.get('test_response', 'N/A')}")
        else:
            print(f"Error: {result.get('error', 'N/A')}")
        return result['status'] == 'success'
    except Exception as e:
        print(f"Connection validation test failed: {e}")
        return False
def test_performance_metrics():
    """Test performance metrics for different scenarios"""
    print("\n" + "=" * 50)
    print("Testing Performance Metrics")
    print("=" * 50)
    try:
        # Test different prompt lengths
        prompts = [
            "Short prompt test.",
            "Medium length prompt for testing response times and quality. " * 5,
            "Very long prompt for stress testing the LLM interface and measuring response times under load. " * 20
        ]
        for i, prompt in enumerate(prompts, 1):
            print(f"\nTest {i} - Prompt length: {len(prompt)} characters")
            start_time = time.time()
            response = generate_completion(
                prompt=prompt,
                task_type="bid_generation"
            )
            end_time = time.time()
            response_time = end_time - start_time
            print(f"  Response Time: {response_time:.2f} seconds")
            print(f"  Status: {response['status']}")
            print(f"  Tokens Used: {response.get('usage', {}).get('total_tokens', 'N/A')}")
            # Validate response time < 2 seconds requirement
            if response_time > 2.0:
                print(f"  WARNING: Response time exceeds 2 second requirement")
            else:
                print(f"  ✓ Response time meets <2 second requirement")
        return True
    except Exception as e:
        print(f"Performance metrics test failed: {e}")
        return False
def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("Starting Comprehensive LLM Configuration Test Suite")
    print("=" * 70)
    tests = [
        ("Configuration Initialization", test_configuration_initialization),
        ("Task-Specific Configurations", test_task_specific_configs),
        ("LLM Interface", test_llm_interface),
        ("Connection Validation", test_connection_validation),
        ("Performance Metrics", test_performance_metrics)
    ]
    results = {}
    for test_name, test_func in tests:
        try:
            print(f"\n{'=' * 20} {test_name} {'=' * 20}")
            results[test_name] = test_func()
        except Exception as e:
            print(f"Test {test_name} failed with exception: {e}")
            results[test_name] = False
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    passed = sum(results.values())
    total = len(results)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name}: {status}")
    print(f"\nOverall: {passed}/{total} tests passed")
    if passed == total:
        print("🎉 All tests passed! LLM configuration is ready for production.")
    else:
        print("⚠️  Some tests failed. Review configuration and dependencies.")
    return passed == total
if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)