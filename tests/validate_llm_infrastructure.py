"""
Comprehensive validation script for LLM infrastructure
Tests all components needed for bid generation pipeline
"""
import sys
import os
import time
import json
from typing import Dict, Any
# Add project root to path
sys.path.append('/app/government_rfp_bid_1927')
from src.config.llm_config import LLMManager, LLMConfig
from src.config.production_llm_config import BidGenerationLLMManager, BidGenerationLLMConfig
def run_comprehensive_validation() -> Dict[str, Any]:
    """Run comprehensive validation of LLM infrastructure"""
    print("🔍 COMPREHENSIVE LLM INFRASTRUCTURE VALIDATION")
    print("=" * 60)
    validation_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "environment": {
            "python_version": sys.version.split()[0],
            "working_directory": os.getcwd(),
            "gpu_available": False
        },
        "base_llm_validation": {},
        "bid_generation_validation": {},
        "performance_metrics": {},
        "overall_status": "pending",
        "recommendations": []
    }
    try:
        # Test 1: Base LLM Infrastructure
        print("\n1️⃣ Testing Base LLM Infrastructure...")
        base_manager = LLMManager()
        base_validation = base_manager.validate_setup()
        validation_results["base_llm_validation"] = base_validation
        print(f"   ✓ Base LLM operational: {base_validation['setup_valid']}")
        print(f"   ✓ OpenAI status: {base_validation['openai_status']}")
        print(f"   ✓ Local model status: {base_validation['local_model_status']}")
        if base_validation['performance_metrics']:
            gen_time = base_validation['performance_metrics'].get('generation_time', 0)
            print(f"   ✓ Generation time: {gen_time:.2f}s")
        # Test 2: Bid Generation LLM Infrastructure
        print("\n2️⃣ Testing Bid Generation LLM Infrastructure...")
        bid_manager = BidGenerationLLMManager()
        bid_validation = bid_manager.validate_infrastructure()
        validation_results["bid_generation_validation"] = bid_validation
        print(f"   ✓ Bid generation ready: {bid_validation['setup_valid']}")
        print(f"   ✓ Section generation: {bid_validation['section_generation_test']}")
        print(f"   ✓ Requirement extraction: {bid_validation['requirement_extraction_test']}")
        # Test 3: Performance Benchmarks
        print("\n3️⃣ Running Performance Benchmarks...")
        perf_metrics = run_performance_tests(bid_manager)
        validation_results["performance_metrics"] = perf_metrics
        print(f"   ✓ Executive summary generation: {perf_metrics['executive_summary_time']:.2f}s")
        print(f"   ✓ Requirements extraction: {perf_metrics['requirements_extraction_time']:.2f}s")
        print(f"   ✓ Section quality score: {perf_metrics['avg_quality_score']:.2f}")
        # Test 4: Integration Readiness
        print("\n4️⃣ Testing Integration Readiness...")
        integration_tests = run_integration_tests(bid_manager)
        print(f"   ✓ Multi-section generation: {integration_tests['multi_section_success']}")
        print(f"   ✓ Error handling: {integration_tests['error_handling_success']}")
        print(f"   ✓ Content formatting: {integration_tests['formatting_success']}")
        # Determine overall status
        overall_success = (
            base_validation['setup_valid'] and
            bid_validation['setup_valid'] and
            perf_metrics['avg_quality_score'] > 0.6 and
            integration_tests['multi_section_success']
        )
        validation_results["overall_status"] = "ready" if overall_success else "needs_attention"
        # Generate recommendations
        recommendations = generate_recommendations(validation_results)
        validation_results["recommendations"] = recommendations
        # Final summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)
        if overall_success:
            print("✅ LLM Infrastructure is READY for bid generation pipeline!")
            print("✅ All core components are operational")
            print("✅ Performance meets requirements")
        else:
            print("⚠️  LLM Infrastructure needs attention before production use")
            print("⚠️  Review recommendations below")
        print(f"\n📈 Key Metrics:")
        print(f"   • Generation Speed: {perf_metrics.get('avg_generation_time', 0):.2f}s avg")
        print(f"   • Content Quality: {perf_metrics.get('avg_quality_score', 0):.2f}/1.0")
        print(f"   • Success Rate: {perf_metrics.get('success_rate', 0):.1%}")
        if recommendations:
            print(f"\n💡 Recommendations:")
            for i, rec in enumerate(recommendations, 1):
                print(f"   {i}. {rec}")
        return validation_results
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        validation_results["overall_status"] = "error"
        validation_results["error"] = str(e)
        import traceback
        traceback.print_exc()
        return validation_results
def run_performance_tests(bid_manager: BidGenerationLLMManager) -> Dict[str, Any]:
    """Run performance benchmarks"""
    metrics = {
        "executive_summary_time": 0,
        "requirements_extraction_time": 0,
        "avg_generation_time": 0,
        "avg_quality_score": 0,
        "success_rate": 0,
        "total_tests": 0,
        "successful_tests": 0
    }
    test_cases = [
        {
            "section_type": "executive_summary",
            "rfp_context": "Government bottled water delivery service for federal offices",
            "requirements": {"duration": "24 months", "delivery_frequency": "weekly", "compliance": "FDA standards"}
        },
        {
            "section_type": "company_qualifications", 
            "rfp_context": "Construction services for government building maintenance",
            "requirements": {"experience": "5+ years", "licensing": "state contractor license", "insurance": "general liability"}
        },
        {
            "section_type": "technical_approach",
            "rfp_context": "Delivery services for government supply chain",
            "requirements": {"coverage_area": "tri-state region", "capacity": "50+ deliveries/day", "tracking": "real-time GPS"}
        }
    ]
    generation_times = []
    quality_scores = []
    for test_case in test_cases:
        metrics["total_tests"] += 1
        try:
            start_time = time.time()
            result = bid_manager.generate_bid_section(
                test_case["section_type"],
                test_case["rfp_context"], 
                test_case["requirements"],
                max_words=150
            )
            end_time = time.time()
            generation_time = end_time - start_time
            if result["status"] == "generated":
                metrics["successful_tests"] += 1
                generation_times.append(generation_time)
                quality_scores.append(result["confidence_score"])
                if test_case["section_type"] == "executive_summary":
                    metrics["executive_summary_time"] = generation_time
    # Calculate aggregated metrics
    if generation_times:
        metrics["avg_generation_time"] = sum(generation_times) / len(generation_times)
    if quality_scores:
        metrics["avg_quality_score"] = sum(quality_scores) / len(quality_scores)
    metrics["success_rate"] = metrics["successful_tests"] / metrics["total_tests"] if metrics["total_tests"] > 0 else 0
    # Test requirements extraction
    test_rfp = """
    The contractor shall provide bottled water delivery services for a period of 24 months.
    All water must meet FDA standards and be delivered weekly to designated government facilities.
    The contractor must maintain general liability insurance and possess a valid business license.
    Delivery tracking system with real-time GPS monitoring is required.
    """
    start_time = time.time()
    try:
        requirements = bid_manager.extract_requirements(test_rfp)
        metrics["requirements_extraction_time"] = time.time() - start_time
    except Exception:
        metrics["requirements_extraction_time"] = 0
    return metrics
def run_integration_tests(bid_manager: BidGenerationLLMManager) -> Dict[str, bool]:
    """Test integration capabilities"""
    tests = {
        "multi_section_success": False,
        "error_handling_success": False, 
        "formatting_success": False
    }
    try:
        # Test 1: Multi-section generation
        sections = ["executive_summary", "company_qualifications"]
        generated_sections = []
        for section_type in sections:
            result = bid_manager.generate_bid_section(
                section_type,
                "Test RFP for multi-section generation",
                {"test_req": "test requirement"},
                max_words=50
            )
            generated_sections.append(result)
        tests["multi_section_success"] = all(s["status"] == "generated" for s in generated_sections)
        # Test 2: Error handling
        try:
            # Test with invalid parameters
            result = bid_manager.generate_bid_section(
                "invalid_section",
                "",
                {},
                max_words=-1
            )
            # Should handle gracefully without crashing
            tests["error_handling_success"] = True
        except Exception:
            tests["error_handling_success"] = False
        # Test 3: Content formatting
        test_result = bid_manager.generate_bid_section(
            "executive_summary",
            "Test formatting",
            {"format_test": "test"},
            max_words=100
        )
        if test_result["status"] == "generated":
            content = test_result["content"]
            # Check basic formatting requirements
            has_proper_length = 10 < len(content) < 1000
            has_sentences = '.' in content
            no_truncation_issues = not content.endswith('...')
            tests["formatting_success"] = has_proper_length and has_sentences and no_truncation_issues
    except Exception as e:
        print(f"Integration test error: {e}")
    return tests
def generate_recommendations(validation_results: Dict[str, Any]) -> list:
    """Generate recommendations based on validation results"""
    recommendations = []
    # Check OpenAI availability
    openai_status = validation_results.get("base_llm_validation", {}).get("openai_status", "not_configured")
    if openai_status == "not_configured":
        recommendations.append("Consider adding OpenAI API key for improved generation quality")
    # Check performance
    perf_metrics = validation_results.get("performance_metrics", {})
    avg_time = perf_metrics.get("avg_generation_time", 0)
    if avg_time > 5:
        recommendations.append("Generation time is slow - consider optimizing model parameters")
    quality_score = perf_metrics.get("avg_quality_score", 0)
    if quality_score < 0.7:
        recommendations.append("Content quality could be improved - consider prompt engineering")
    success_rate = perf_metrics.get("success_rate", 0)
    if success_rate < 0.9:
        recommendations.append("Success rate is low - investigate error patterns")
    # Check overall status
    overall_status = validation_results.get("overall_status", "")
    if overall_status == "ready" and not recommendations:
        recommendations.append("Infrastructure is ready - proceed with RAG system implementation")
    return recommendations
def save_validation_report(validation_results: Dict[str, Any]):
    """Save validation results to file"""
    os.makedirs('/app/government_rfp_bid_1927/logs', exist_ok=True)
    report_path = '/app/government_rfp_bid_1927/logs/llm_validation_report.json'
    with open(report_path, 'w') as f:
        json.dump(validation_results, f, indent=2)
    print(f"\n📄 Validation report saved to: {report_path}")
if __name__ == "__main__":
    results = run_comprehensive_validation()
    save_validation_report(results)
    # Exit with appropriate code
    sys.exit(0 if results["overall_status"] == "ready" else 1)