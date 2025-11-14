"""
Comprehensive RAG system validation using the working RAG engine
Tests across all RFP sectors: bottled water, construction, delivery
"""
import sys
import os
import time
import json
from typing import Dict, Any, List
# Add project root to path
sys.path.append('/app/government_rfp_bid_1927')
from src.rag.working_rag_engine import WorkingRAGEngine
class ComprehensiveRAGValidator:
    """Validator for RAG system across all target RFP sectors"""
    def __init__(self):
        self.rag_engine = None
        self.test_results = {}
    def initialize_rag_engine(self) -> bool:
        """Initialize RAG engine"""
        try:
            print("🔧 Initializing Working RAG Engine...")
            self.rag_engine = WorkingRAGEngine()
            load_stats = self.rag_engine.load_index()
            print(f"   ✓ Index loaded: {load_stats['total_chunks']} chunks")
            print(f"   ✓ Embedding dimension: {load_stats['embedding_dimension']}")
            return True
        except Exception as e:
            print(f"   ❌ Failed to initialize: {e}")
            return False
    def run_sector_validation(self) -> Dict[str, Any]:
        """Run comprehensive validation across all RFP sectors"""
        print("🎯 COMPREHENSIVE RAG VALIDATION ACROSS RFP SECTORS")
        print("=" * 60)
        if not self.initialize_rag_engine():
            return {"status": "error", "message": "Failed to initialize RAG engine"}
        # Get system overview
        print("\n1️⃣ System Overview...")
        index_stats = self.rag_engine.get_index_stats()
        validation_health = self.rag_engine.validate_index()
        print(f"   ✓ Total chunks: {index_stats['total_chunks']:,}")
        print(f"   ✓ Embedding dimension: {index_stats['embedding_dimension']}")
        print(f"   ✓ System health: {validation_health['overall_health']}")
        if 'source_distribution' in index_stats:
            print(f"   📊 Source distribution:")
            for source, count in index_stats['source_distribution'].items():
                print(f"      • {source}: {count:,} chunks")
        # Define sector-specific test queries
        sector_tests = {
            "bottled_water": {
                "queries": [
                    "bottled water delivery service weekly FDA compliant",
                    "5 gallon water bottles office delivery tracking",
                    "water quality standards FDA emergency delivery",
                    "bottled water supply government contract requirements",
                    "water cooler service maintenance cleaning"
                ],
                "expected_keywords": ["water", "bottle", "delivery", "gallon", "FDA"]
            },
            "construction": {
                "queries": [
                    "construction services building maintenance government facility",
                    "general contractor license bonding insurance construction",
                    "renovation repair HVAC electrical commercial building",
                    "construction project management OSHA safety compliance",
                    "building maintenance janitorial grounds keeping"
                ],
                "expected_keywords": ["construction", "building", "contractor", "maintenance", "facility"]
            },
            "delivery": {
                "queries": [
                    "delivery services logistics transportation government contract",
                    "freight shipping supply chain management tracking",
                    "warehouse distribution emergency delivery capability",
                    "logistics transportation 24 hour response service",
                    "delivery truck fleet management GPS tracking"
                ],
                "expected_keywords": ["delivery", "logistics", "transportation", "shipping", "distribution"]
            },
            "general": {
                "queries": [
                    "government procurement requirements bid submission",
                    "contract terms conditions payment schedule performance",
                    "small business enterprise certification requirements",
                    "quality assurance ISO certification audit documentation",
                    "safety compliance environmental regulations standards"
                ],
                "expected_keywords": ["government", "contract", "procurement", "compliance", "certification"]
            }
        }
        # Run tests for each sector
        print("\n2️⃣ Running Sector-Specific Validation...")
        sector_results = {}
        overall_metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "avg_search_time": 0,
            "avg_results_per_query": 0,
            "avg_relevance_score": 0
        }
        all_search_times = []
        all_result_counts = []
        all_relevance_scores = []
        for sector, test_data in sector_tests.items():
            print(f"\n   🔍 Testing {sector.upper().replace('_', ' ')} sector...")
            sector_result = {
                "sector": sector,
                "total_queries": len(test_data["queries"]),
                "successful_queries": 0,
                "failed_queries": 0,
                "avg_search_time": 0,
                "avg_results": 0,
                "avg_relevance": 0,
                "query_results": []
            }
            search_times = []
            result_counts = []
            relevance_scores = []
            for i, query in enumerate(test_data["queries"], 1):
                print(f"      Query {i}: {query[:50]}...")
                try:
                    start_time = time.time()
                    results = self.rag_engine.search(query, k=5)
                    search_time = time.time() - start_time
                    # Calculate relevance score
                    relevance = self._calculate_relevance(results, test_data["expected_keywords"])
                    search_times.append(search_time)
                    result_counts.append(len(results))
                    relevance_scores.append(relevance)
                    sector_result["successful_queries"] += 1
                    overall_metrics["successful_queries"] += 1
                    query_result = {
                        "query": query,
                        "search_time": search_time,
                        "results_count": len(results),
                        "top_score": results[0]["score"] if results else 0.0,
                        "relevance_score": relevance,
                        "status": "success"
                    }
                    sector_result["query_results"].append(query_result)
                    print(f"         ✓ {len(results)} results in {search_time:.3f}s (relevance: {relevance:.3f})")
                except Exception as e:
                    sector_result["failed_queries"] += 1
                    print(f"         ❌ Failed: {e}")
                    error_result = {
                        "query": query,
                        "status": "error",
                        "error": str(e)
                    }
                    sector_result["query_results"].append(error_result)
                overall_metrics["total_queries"] += 1
            # Calculate sector averages
            if search_times:
                sector_result["avg_search_time"] = sum(search_times) / len(search_times)
                sector_result["avg_results"] = sum(result_counts) / len(result_counts)
                sector_result["avg_relevance"] = sum(relevance_scores) / len(relevance_scores)
                all_search_times.extend(search_times)
                all_result_counts.extend(result_counts)
                all_relevance_scores.extend(relevance_scores)
            sector_results[sector] = sector_result
            # Sector summary
            success_rate = sector_result["successful_queries"] / sector_result["total_queries"]
            print(f"      📊 {sector.upper()} Summary: {success_rate:.1%} success rate, {sector_result['avg_relevance']:.3f} avg relevance")
        # Calculate overall metrics
        if all_search_times:
            overall_metrics["avg_search_time"] = sum(all_search_times) / len(all_search_times)
            overall_metrics["avg_results_per_query"] = sum(all_result_counts) / len(all_result_counts)
            overall_metrics["avg_relevance_score"] = sum(all_relevance_scores) / len(all_relevance_scores)
        overall_success_rate = overall_metrics["successful_queries"] / overall_metrics["total_queries"] if overall_metrics["total_queries"] > 0 else 0
        # Performance assessment
        print("\n3️⃣ Performance Assessment...")
        print(f"   ⏱️ Average search time: {overall_metrics['avg_search_time']:.3f}s")
        print(f"   📊 Average results per query: {overall_metrics['avg_results_per_query']:.1f}")
        print(f"   🎯 Average relevance score: {overall_metrics['avg_relevance_score']:.3f}")
        print(f"   ✅ Overall success rate: {overall_success_rate:.1%}")
        # Sector comparison
        print(f"\n   📈 Sector Performance Comparison:")
        for sector, result in sector_results.items():
            success_rate = result["successful_queries"] / result["total_queries"] if result["total_queries"] > 0 else 0
            print(f"      • {sector.upper().replace('_', ' ')}: {success_rate:.1%} success, {result['avg_relevance']:.3f} relevance")
        # Overall assessment
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 60)
        if overall_success_rate >= 0.9 and overall_metrics['avg_relevance_score'] >= 0.6:
            status = "EXCELLENT"
            print("🎉 RAG SYSTEM PERFORMANCE: EXCELLENT")
        elif overall_success_rate >= 0.8 and overall_metrics['avg_relevance_score'] >= 0.5:
            status = "VERY_GOOD"
            print("✅ RAG SYSTEM PERFORMANCE: VERY GOOD")
        elif overall_success_rate >= 0.7 and overall_metrics['avg_relevance_score'] >= 0.4:
            status = "GOOD"
            print("⚠️  RAG SYSTEM PERFORMANCE: GOOD")
        else:
            status = "NEEDS_IMPROVEMENT"
            print("❌ RAG SYSTEM PERFORMANCE: NEEDS IMPROVEMENT")
        # Compile final results
        final_results = {
            "status": status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "overall_metrics": overall_metrics,
            "overall_success_rate": overall_success_rate,
            "sector_results": sector_results,
            "system_stats": index_stats,
            "system_health": validation_health
        }
        # Performance recommendations
        recommendations = []
        if overall_metrics['avg_search_time'] > 1.0:
            recommendations.append("Optimize search performance to achieve sub-second response times")
        if overall_metrics['avg_relevance_score'] < 0.6:
            recommendations.append("Improve embedding quality or similarity thresholds for better relevance")
        if overall_success_rate < 0.9:
            recommendations.append("Investigate and fix query failures")
        if not recommendations:
            recommendations.append("System performance is excellent - ready for production use")
        final_results["recommendations"] = recommendations
        print(f"\n💡 Recommendations:")
        for rec in recommendations:
            print(f"   • {rec}")
        if status in ["EXCELLENT", "VERY_GOOD"]:
            print(f"\n🚀 RAG SYSTEM IS READY FOR PRODUCTION BID GENERATION!")
        else:
            print(f"\n⚠️  RAG system needs improvements before production use")
        # Save results
        results_path = "/app/government_rfp_bid_1927/logs/comprehensive_rag_validation.json"
        os.makedirs(os.path.dirname(results_path), exist_ok=True)
        with open(results_path, 'w') as f:
            json.dump(final_results, f, indent=2)
        print(f"\n📄 Detailed results saved to: {results_path}")
        return final_results
    def _calculate_relevance(self, results: List[Dict], expected_keywords: List[str]) -> float:
        """Calculate relevance score based on keyword presence and result scores"""
        if not results:
            return 0.0
        # Weight by result scores
        weighted_score = 0.0
        total_weight = 0.0
        for result in results[:3]:  # Top 3 results
            score = result.get("score", 0.0)
            text = result.get("text", "").lower()
            # Count keyword matches
            keyword_matches = sum(1 for keyword in expected_keywords if keyword.lower() in text)
            keyword_score = keyword_matches / len(expected_keywords) if expected_keywords else 0
            # Combine semantic score with keyword relevance
            combined_score = (score * 0.7) + (keyword_score * 0.3)
            weighted_score += combined_score * score  # Weight by similarity score
            total_weight += score
        return weighted_score / total_weight if total_weight > 0 else 0.0
def main():
    """Main validation function"""
    validator = ComprehensiveRAGValidator()
    results = validator.run_sector_validation()
    # Return success based on status
    success = results.get("status") in ["EXCELLENT", "VERY_GOOD", "GOOD"]
    return success
if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)