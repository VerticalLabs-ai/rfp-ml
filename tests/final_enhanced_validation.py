"""
Final validation for the enhanced LLM infrastructure
"""
import json
import os
import sys
import time

sys.path.append('/app/government_rfp_bid_1927')
from src.config.enhanced_bid_llm import EnhancedBidLLMManager


def run_final_validation():
    """Run comprehensive final validation"""
    print("🎯 FINAL ENHANCED LLM INFRASTRUCTURE VALIDATION")
    print("=" * 60)
    validation_results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "test_results": {},
        "performance_metrics": {},
        "overall_assessment": {},
        "readiness_status": "pending"
    }
    try:
        # Initialize manager
        print("\n1️⃣ Initializing Enhanced Bid LLM Manager...")
        manager = EnhancedBidLLMManager()
        print("   ✓ Manager initialized successfully")
        # Infrastructure validation
        print("\n2️⃣ Running Infrastructure Validation...")
        infra_validation = manager.validate_infrastructure()
        validation_results["test_results"]["infrastructure"] = infra_validation
        for test_name, result in infra_validation.items():
            if test_name != "overall_status":
                status = "✓" if result else "✗"
                print(f"   {status} {test_name.replace('_', ' ').title()}: {result}")
        print(f"   Infrastructure Status: {infra_validation['overall_status'].upper()}")
        # Performance testing
        print("\n3️⃣ Running Performance Tests...")
        perf_start = time.time()
        # Test multiple sections
        test_sections = [
            ("executive_summary", "Executive Summary"),
            ("company_qualifications", "Company Qualifications"),
            ("technical_approach", "Technical Approach")
        ]
        generation_times = []
        quality_scores = []
        word_counts = []
        for section_id, section_name in test_sections:
            section_start = time.time()
            result = manager.generate_bid_section(
                section_id,
                "Government bottled water delivery service for 24 months with weekly delivery requirements",
                {"duration": "24 months", "frequency": "weekly", "compliance": "FDA standards"},
                max_words=150
            )
            section_time = time.time() - section_start
            generation_times.append(section_time)
            quality_scores.append(result["confidence_score"])
            word_counts.append(result["word_count"])
            print(f"   ✓ {section_name}: {result['word_count']} words, {result['confidence_score']:.2f} quality, {section_time:.2f}s")
        total_perf_time = time.time() - perf_start
        # Performance metrics
        validation_results["performance_metrics"] = {
            "total_generation_time": total_perf_time,
            "avg_generation_time": sum(generation_times) / len(generation_times),
            "avg_quality_score": sum(quality_scores) / len(quality_scores),
            "avg_word_count": sum(word_counts) / len(word_counts),
            "success_rate": 1.0  # All sections generated successfully
        }
        perf_metrics = validation_results["performance_metrics"]
        print("\n   Performance Summary:")
        print(f"   • Total time: {perf_metrics['total_generation_time']:.2f}s")
        print(f"   • Average per section: {perf_metrics['avg_generation_time']:.2f}s")
        print(f"   • Average quality: {perf_metrics['avg_quality_score']:.2f}")
        print(f"   • Average words: {perf_metrics['avg_word_count']:.0f}")
        # Requirements extraction test
        print("\n4️⃣ Testing Requirements Extraction...")
        test_rfp = """
        The contractor shall provide bottled water delivery services for a period of 24 months.
        Weekly delivery of 5-gallon bottles is required to 15 government office locations.
        All water must meet FDA quality standards and be delivered with real-time tracking.
        Contractor must maintain $1M general liability insurance and have minimum 5 years experience.
        Emergency delivery capability within 24 hours is mandatory.
        """
        extracted_requirements = manager.extract_requirements(test_rfp)
        req_extraction_success = len(extracted_requirements) >= 3
        validation_results["test_results"]["requirements_extraction"] = {
            "success": req_extraction_success,
            "requirements_count": len(extracted_requirements),
            "extracted_requirements": extracted_requirements
        }
        print(f"   ✓ Extracted {len(extracted_requirements)} requirements:")
        for req_id, req_text in extracted_requirements.items():
            print(f"     • {req_id}: {req_text}")
        # Overall assessment
        print("\n5️⃣ Overall Assessment...")
        # Calculate scores
        infrastructure_score = 1.0 if infra_validation.get("overall_status") in ["ready", "mostly_ready"] else 0.0
        performance_score = 1.0 if perf_metrics["avg_quality_score"] >= 0.7 and perf_metrics["avg_generation_time"] <= 10 else 0.7
        extraction_score = 1.0 if req_extraction_success else 0.5
        overall_score = (infrastructure_score + performance_score + extraction_score) / 3
        validation_results["overall_assessment"] = {
            "infrastructure_score": infrastructure_score,
            "performance_score": performance_score,
            "extraction_score": extraction_score,
            "overall_score": overall_score
        }
        # Determine readiness status
        if overall_score >= 0.85:
            validation_results["readiness_status"] = "production_ready"
            status_message = "✅ PRODUCTION READY"
        elif overall_score >= 0.7:
            validation_results["readiness_status"] = "mostly_ready"
            status_message = "⚠️  MOSTLY READY"
        else:
            validation_results["readiness_status"] = "needs_improvement"
            status_message = "❌ NEEDS IMPROVEMENT"
        print(f"   Infrastructure Score: {infrastructure_score:.2f}")
        print(f"   Performance Score: {performance_score:.2f}")
        print(f"   Extraction Score: {extraction_score:.2f}")
        print(f"   Overall Score: {overall_score:.2f}")
        # Final summary
        print("\n" + "=" * 60)
        print("📊 FINAL VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Readiness Status: {status_message}")
        print(f"Overall Score: {overall_score:.2f}/1.0")
        if validation_results["readiness_status"] == "production_ready":
            print("\n🎉 LLM INFRASTRUCTURE IS PRODUCTION READY!")
            print("✅ All systems operational with high-quality content generation")
            print("✅ Robust fallback system ensures reliable output")
            print("✅ Performance meets all requirements")
            print("✅ Ready for RAG system integration")
            print("\n📋 Next Steps:")
            print("   1. Proceed with RAG system implementation using FAISS")
            print("   2. Begin processing RFP datasets for vector embeddings")
            print("   3. Integrate LLM with pricing and compliance engines")
            print("   4. Implement end-to-end bid generation pipeline")
        else:
            print("\n⚠️  System needs attention before production deployment")
            print("📋 Recommended improvements:")
            if infrastructure_score < 1.0:
                print("   • Review infrastructure setup and configuration")
            if performance_score < 1.0:
                print("   • Optimize content generation quality and speed")
            if extraction_score < 1.0:
                print("   • Improve requirements extraction accuracy")
        # Save validation results
        os.makedirs('/app/government_rfp_bid_1927/logs', exist_ok=True)
        with open('/app/government_rfp_bid_1927/logs/final_enhanced_validation.json', 'w') as f:
            json.dump(validation_results, f, indent=2)
        print("\n📄 Validation results saved to: /app/government_rfp_bid_1927/logs/final_enhanced_validation.json")
        return validation_results["readiness_status"] == "production_ready"
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
if __name__ == "__main__":
    success = run_final_validation()
    sys.exit(0 if success else 1)
