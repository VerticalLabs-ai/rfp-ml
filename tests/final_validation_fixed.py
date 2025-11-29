"""
Fixed comprehensive validation script for LLM infrastructure
"""
import json
import os
import sys
import time

# Add project root to path
sys.path.append('/app/government_rfp_bid_1927')
def main():
    print("🎯 FINAL LLM INFRASTRUCTURE VALIDATION (FIXED)")
    print("=" * 60)
    validation_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "infrastructure_tests": {},
        "functionality_tests": {},
        "overall_status": "pending",
        "summary": {}
    }
    try:
        # Test 1: Basic Infrastructure
        print("\n1️⃣ Testing Basic Infrastructure...")
        from src.config.llm_config import LLMManager
        base_manager = LLMManager()
        model_info = base_manager.get_model_info()
        print(f"   ✓ Primary backend: {model_info['primary_backend']}")
        print(f"   ✓ Local model: {model_info['local_model']}")
        print(f"   ✓ Device: {model_info['device']}")
        validation_results["infrastructure_tests"]["base_llm"] = True
        # Test 2: Bid Generation Manager
        print("\n2️⃣ Testing Bid Generation Manager...")
        from src.config.production_llm_config import BidGenerationLLMManager
        bid_manager = BidGenerationLLMManager()
        validation_results["infrastructure_tests"]["bid_manager"] = True
        print("   ✓ Bid generation manager initialized")
        # Test 3: Text Generation Quality
        print("\n3️⃣ Testing Text Generation Quality...")
        test_result = bid_manager.generate_bid_section(
            "executive_summary",
            "Government bottled water delivery service for 24 months",
            {"duration": "24 months", "service": "water delivery"},
            max_words=100
        )
        generation_successful = (
            test_result["status"] == "generated" and
            len(test_result["content"]) > 20 and
            test_result["word_count"] > 0
        )
        validation_results["functionality_tests"]["text_generation"] = generation_successful
        if generation_successful:
            print(f"   ✓ Generated {test_result['word_count']} words")
            print(f"   ✓ Quality score: {test_result['confidence_score']:.2f}")
            print(f"   ✓ Content preview: {test_result['content'][:100]}...")
        else:
            print("   ✗ Generation failed or produced poor quality content")
        # Test 4: Requirements Extraction
        print("\n4️⃣ Testing Requirements Extraction...")
        test_rfp = """
        The contractor must provide bottled water delivery for 24 months.
        Weekly delivery is required. All water must meet FDA standards.
        Contractor must have general liability insurance.
        """
        requirements = bid_manager.extract_requirements(test_rfp)
        extraction_successful = len(requirements) > 0
        validation_results["functionality_tests"]["requirements_extraction"] = extraction_successful
        if extraction_successful:
            print(f"   ✓ Extracted {len(requirements)} requirements")
            for req_id, req_text in list(requirements.items())[:3]:  # Show first 3
                print(f"     • {req_text[:60]}...")
        else:
            print("   ✗ Requirements extraction failed")
        # Test 5: Integration Readiness
        print("\n5️⃣ Testing Integration Readiness...")
        # Test multiple sections
        sections_to_test = ["executive_summary", "company_qualifications"]
        section_results = []
        for section in sections_to_test:
            result = bid_manager.generate_bid_section(
                section,
                "Test RFP for integration testing",
                {"test": "requirement"},
                max_words=50
            )
            section_results.append(result["status"] == "generated")
        integration_ready = all(section_results)
        validation_results["functionality_tests"]["integration_ready"] = integration_ready
        if integration_ready:
            print(f"   ✓ Successfully generated {len(sections_to_test)} different sections")
        else:
            print("   ✗ Failed to generate some sections")
        # Overall Assessment
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        infrastructure_score = sum(validation_results["infrastructure_tests"].values())
        functionality_score = sum(validation_results["functionality_tests"].values())
        total_tests = len(validation_results["infrastructure_tests"]) + len(validation_results["functionality_tests"])
        passed_tests = infrastructure_score + functionality_score
        pass_rate = passed_tests / total_tests if total_tests > 0 else 0
        validation_results["summary"] = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "pass_rate": pass_rate,
            "infrastructure_score": infrastructure_score,
            "functionality_score": functionality_score
        }
        if pass_rate >= 0.8:
            validation_results["overall_status"] = "ready"
            status_message = "✅ LLM Infrastructure is READY for production use!"
        elif pass_rate >= 0.6:
            validation_results["overall_status"] = "mostly_ready"
            status_message = "⚠️  LLM Infrastructure is mostly ready with minor issues"
        else:
            validation_results["overall_status"] = "needs_work"
            status_message = "❌ LLM Infrastructure needs more work"
        print(f"Overall Status: {validation_results['overall_status'].upper()}")
        print(f"Tests Passed: {passed_tests}/{total_tests} ({pass_rate:.1%})")
        print(f"\n{status_message}")
        # Specific test results
        print("\n📋 Test Results:")
        print(f"   Infrastructure Tests: {infrastructure_score}/{len(validation_results['infrastructure_tests'])}")
        print(f"   Functionality Tests: {functionality_score}/{len(validation_results['functionality_tests'])}")
        # Next steps
        print("\n📋 Next Steps:")
        if validation_results["overall_status"] == "ready":
            print("   1. Proceed with RAG system implementation")
            print("   2. Begin vector database setup with FAISS")
            print("   3. Start processing RFP datasets for embeddings")
        else:
            print("   1. Review failed tests and improve implementation")
            print("   2. Consider upgrading to a more capable local model")
            print("   3. Re-run validation tests")
        # Save results
        os.makedirs('/app/government_rfp_bid_1927/logs', exist_ok=True)
        with open('/app/government_rfp_bid_1927/logs/final_validation_fixed.json', 'w') as f:
            json.dump(validation_results, f, indent=2)
        print("\n📄 Validation results saved to: /app/government_rfp_bid_1927/logs/final_validation_fixed.json")
        return validation_results["overall_status"] == "ready"
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
