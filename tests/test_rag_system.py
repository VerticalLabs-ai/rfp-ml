"""
Comprehensive RAG system testing and validation
Tests retrieval across all target RFP sectors (bottled water, construction, delivery)
"""
import sys
import os
import time
import json
from typing import Dict, Any, List
from dataclasses import dataclass
# Add project root to path
sys.path.append('/app/government_rfp_bid_1927')
from src.rag.rag_engine import RAGEngine, RAGConfig
@dataclass
class RAGTestCase:
    """Test case for RAG validation"""
    query: str
    category: str
    expected_keywords: List[str]
    min_results: int = 3
    min_score: float = 0.3
class RAGSystemValidator:
    """Comprehensive validator for RAG system across all RFP sectors"""
    def __init__(self):
        self.rag_engine = None
        self.test_cases = self._create_test_cases()
        self.results = {}
    def _create_test_cases(self) -> List[RAGTestCase]:
        """Create comprehensive test cases for all RFP sectors"""
        return [
            # Bottled Water RFPs
            RAGTestCase(
                query="bottled water delivery service government contract",
                category="bottled_water",
                expected_keywords=["water", "delivery", "bottle", "gallon"],
                min_results=3,
                min_score=0.4
            ),
            RAGTestCase(
                query="weekly water supply 5-gallon bottles office locations",
                category="bottled_water", 
                expected_keywords=["weekly", "supply", "office", "location"],
                min_results=2,
                min_score=0.3
            ),
            RAGTestCase(
                query="FDA compliant water quality standards delivery tracking",
                category="bottled_water",
                expected_keywords=["FDA", "quality", "standards", "tracking"],
                min_results=2,
                min_score=0.3
            ),
            # Construction RFPs
            RAGTestCase(
                query="construction services building maintenance government facility",
                category="construction",
                expected_keywords=["construction", "building", "maintenance", "facility"],
                min_results=3,
                min_score=0.4
            ),
            RAGTestCase(
                query="general contractor license bonding insurance construction project",
                category="construction",
                expected_keywords=["contractor", "license", "bonding", "insurance"],
                min_results=2,
                min_score=0.3
            ),
            RAGTestCase(
                query="renovation repair services commercial building HVAC electrical",
                category="construction",
                expected_keywords=["renovation", "repair", "commercial", "HVAC"],
                min_results=2,
                min_score=0.3
            ),
            # Delivery/Logistics RFPs
            RAGTestCase(
                query="delivery services logistics transportation government contract",
                category="delivery",
                expected_keywords=["delivery", "logistics", "transportation", "contract"],
                min_results=3,
                min_score=0.4
            ),
            RAGTestCase(
                query="freight shipping supply chain management tracking system",
                category="delivery",
                expected_keywords=["freight", "shipping", "supply", "tracking"],
                min_results=2,
                min_score=0.3
            ),
            RAGTestCase(
                query="warehouse distribution emergency delivery 24 hour response",
                category="delivery",
                expected_keywords=["warehouse", "distribution", "emergency", "response"],
                min_results=2,
                min_score=0.3
            ),
            # General Government Procurement
            RAGTestCase(
                query="government procurement requirements bid submission process",
                category="general",
                expected_keywords=["government", "procurement", "bid", "submission"],
                min_results=3,
                min_score=0.3
            ),
            RAGTestCase(
                query="contract terms conditions payment schedule performance bond",
                category="general",
                expected_keywords=["contract", "terms", "payment", "performance"],
                min_results=3,
                min_score=0.3
            ),
            RAGTestCase(
                query="minority business enterprise small business certification requirements",
                category="general",
                expected_keywords=["minority", "business", "small", "certification"],
                min_results=2,
                min_score=0.3
            ),
            # Compliance and Standards
            RAGTestCase(
                query="safety compliance OSHA standards environmental regulations",
                category="compliance",
                expected_keywords=["safety", "compliance", "OSHA", "environmental"],
                min_results=2,
                min_score=0.3
            ),
            RAGTestCase(
                query="quality assurance ISO certification audit documentation",
                category="compliance",
                expected_keywords=["quality", "assurance", "ISO", "audit"],
                min_results=2,
                min_score=0.3
            )
        ]
    def initialize_rag_engine(self) -> bool:
        """Initialize and load RAG engine"""
        try:
            print("🔧 Initializing RAG Engine...")
            self.rag_engine = RAGEngine()
            if self.rag_engine._index_exists():
                load_stats = self.rag_engine.load_index()
                print(f"   ✓ Loaded index with {load_stats['total_chunks']} chunks")
                return True
            else:
                print("   ❌ No index found. Build index first.")
                return False
        except Exception as e:
            print(f"   ❌ Failed to initialize RAG engine: {e}")
            return False
    def run_comprehensive_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation across all test cases"""
        print("🎯 COMPREHENSIVE RAG SYSTEM VALIDATION")
        print("=" * 60)
        if not self.initialize_rag_engine():
            return {"status": "error", "message": "Failed to initialize RAG engine"}
        # Get baseline system stats
        print("\n1️⃣ System Overview...")
        index_stats = self.rag_engine.get_index_stats()
        validation_results = self.rag_engine.validate_index()
        print(f"   ✓ Index size: {index_stats['total_chunks']:,} chunks")
        print(f"   ✓ Embedding dimension: {index_stats['embedding_dimension']}")
        print(f"   ✓ System health: {validation_results['overall_health']}")
        # Run test cases by category
        print("\n2️⃣ Running Sector-Specific Tests...")
        category_results = {}
        overall_results = {
            "total_tests": len(self.test_cases),
            "passed_tests": 0,
            "failed_tests": 0,
            "test_details": [],
            "category_performance": {},
            "performance_metrics": {}
        }
        # Group test cases by category
        categories = {}
        for test_case in self.test_cases:
            if test_case.category not in categories:
                categories[test_case.category] = []
            categories[test_case.category].append(test_case)
        # Run tests for each category
        all_search_times = []
        for category, test_cases in categories.items():
            print(f"\n   🔍 Testing {category.upper()} sector...")
            category_results[category] = {
                "total_tests": len(test_cases),
                "passed_tests": 0,
                "failed_tests": 0,
                "avg_score": 0,
                "avg_results_count": 0,
                "test_details": []
            }
            for i, test_case in enumerate(test_cases, 1):
                print(f"      Test {i}: {test_case.query[:50]}...")
                # Run search with timing
                start_time = time.time()
                try:
                    results = self.rag_engine.search(test_case.query, k=10)
                    search_time = time.time() - start_time
                    all_search_times.append(search_time)
                    # Analyze results
                    test_result = self._analyze_test_results(test_case, results, search_time)
                    if test_result["passed"]:
                        category_results[category]["passed_tests"] += 1
                        overall_results["passed_tests"] += 1
                        print(f"         ✅ PASSED - {test_result['summary']}")
                    else:
                        category_results[category]["failed_tests"] += 1
                        overall_results["failed_tests"] += 1
                        print(f"         ❌ FAILED - {test_result['summary']}")
                    category_results[category]["test_details"].append(test_result)
                    overall_results["test_details"].append(test_result)
                except Exception as e:
                    category_results[category]["failed_tests"] += 1
                    overall_results["failed_tests"] += 1
                    print(f"         ❌ ERROR - {e}")
                    error_result = {
                        "query": test_case.query,
                        "category": test_case.category,
                        "passed": False,
                        "error": str(e),
                        "summary": f"Search error: {e}"
                    }
                    category_results[category]["test_details"].append(error_result)
                    overall_results["test_details"].append(error_result)
            # Calculate category averages
            if category_results[category]["test_details"]:
                valid_results = [r for r in category_results[category]["test_details"] 
                               if "score" in r and r["score"] is not None]
                if valid_results:
                    category_results[category]["avg_score"] = sum(r["score"] for r in valid_results) / len(valid_results)
                    category_results[category]["avg_results_count"] = sum(r["results_count"] for r in valid_results) / len(valid_results)
            print(f"      📊 {category.upper()} Results: {category_results[category]['passed_tests']}/{category_results[category]['total_tests']} passed")
        # Calculate overall performance metrics
        if all_search_times:
            overall_results["performance_metrics"] = {
                "avg_search_time": sum(all_search_times) / len(all_search_times),
                "max_search_time": max(all_search_times),
                "min_search_time": min(all_search_times),
                "total_searches": len(all_search_times)
            }
        overall_results["category_performance"] = category_results
        # Calculate pass rate
        pass_rate = overall_results["passed_tests"] / overall_results["total_tests"] if overall_results["total_tests"] > 0 else 0
        # Performance assessment
        print("\n3️⃣ Performance Assessment...")
        perf_metrics = overall_results["performance_metrics"]
        print(f"   ⏱️ Search Performance:")
        print(f"      • Average search time: {perf_metrics['avg_search_time']:.3f}s")
        print(f"      • Max search time: {perf_metrics['max_search_time']:.3f}s")
        print(f"      • Total searches: {perf_metrics['total_searches']}")
        print(f"\n   📈 Category Performance:")
        for category, stats in category_results.items():
            pass_rate_cat = stats["passed_tests"] / stats["total_tests"] if stats["total_tests"] > 0 else 0
            print(f"      • {category.upper()}: {pass_rate_cat:.1%} pass rate ({stats['passed_tests']}/{stats['total_tests']})")
        # Overall assessment
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Overall Pass Rate: {pass_rate:.1%} ({overall_results['passed_tests']}/{overall_results['total_tests']})")
        if pass_rate >= 0.8:
            status = "EXCELLENT"
            print("✅ RAG SYSTEM PERFORMANCE: EXCELLENT")
            print("✅ Ready for production use across all RFP sectors")
        elif pass_rate >= 0.6:
            status = "GOOD"
            print("⚠️  RAG SYSTEM PERFORMANCE: GOOD")
            print("⚠️  Minor improvements needed in some sectors")
        else:
            status = "NEEDS_IMPROVEMENT"
            print("❌ RAG SYSTEM PERFORMANCE: NEEDS IMPROVEMENT")
            print("❌ Significant issues detected - review and optimize")
        # Add system info to results
        overall_results.update({
            "status": status,
            "pass_rate": pass_rate,
            "system_stats": index_stats,
            "system_validation": validation_results,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        })
        # Save results
        results_path = "/app/government_rfp_bid_1927/logs/rag_validation_results.json"
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        with open(results_path, 'w') as f:
            json.dump(overall_results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_path}")
        return overall_results
    def _analyze_test_results(self, test_case: RAGTestCase, results: List[Dict], search_time: float) -> Dict[str, Any]:
        """Analyze search results against test case expectations"""
        # Basic checks
        has_min_results = len(results) >= test_case.min_results
        has_min_score = len(results) > 0 and results[0]["score"] >= test_case.min_score
        # Keyword relevance check
        keyword_matches = 0
        total_keywords = len(test_case.expected_keywords)
        if results:
            # Check top 3 results for keyword presence
            combined_text = ""
            for result in results[:3]:
                combined_text += result.get("text", "").lower()
            for keyword in test_case.expected_keywords:
                if keyword.lower() in combined_text:
                    keyword_matches += 1
        keyword_relevance = keyword_matches / total_keywords if total_keywords > 0 else 0
        # Overall assessment
        passed = (has_min_results and has_min_score and keyword_relevance >= 0.3)
        # Calculate average score
        avg_score = sum(r["score"] for r in results) / len(results) if results else 0
        return {
            "query": test_case.query,
            "category": test_case.category,
            "passed": passed,
            "results_count": len(results),
            "min_results_met": has_min_results,
            "min_score_met": has_min_score,
            "top_score": results[0]["score"] if results else 0,
            "score": avg_score,
            "keyword_relevance": keyword_relevance,
            "keyword_matches": keyword_matches,
            "total_keywords": total_keywords,
            "search_time": search_time,
            "summary": f"{len(results)} results, top score: {results[0]['score']:.3f}, relevance: {keyword_relevance:.1%}" if results else "No results"
        }
def run_rag_validation():
    """Main function to run RAG validation"""
    validator = RAGSystemValidator()
    results = validator.run_comprehensive_validation()
    # Return success if validation passes
    return results.get("status") in ["EXCELLENT", "GOOD"]
if __name__ == "__main__":
    success = run_rag_validation()
    sys.exit(0 if success else 1)