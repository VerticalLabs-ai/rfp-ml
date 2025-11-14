import sys
import os
import time
import json
from datetime import datetime
# Add src to path
sys.path.append('/app/government_rfp_bid_1927/src')
from rag.rag_engine import OptimizedRAGEngine
def comprehensive_rag_validation():
    """
    Comprehensive validation of RAG system with sector-specific queries
    """
    print("=== RAG System Comprehensive Validation ===")
    print(f"Validation started at: {datetime.now()}")
    # Initialize RAG
    rag = OptimizedRAGEngine()
    # Load index
    print("\n1. Loading RAG index...")
    start_time = time.time()
    if not rag.load_index():
        print("Failed to load index. Attempting to build...")
        if not rag.build_index():
            print("CRITICAL: Failed to build RAG index")
            return False
    load_time = time.time() - start_time
    print(f"   Index loaded in {load_time:.2f} seconds")
    # Get index statistics
    print("\n2. Index Statistics:")
    stats = rag.get_index_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    # Define comprehensive test queries by sector
    test_cases = {
        "bottled_water": [
            "bottled water delivery services commercial office buildings",
            "water cooler rental and maintenance contract",
            "spring water delivery municipal offices"
        ],
        "construction": [
            "construction project management services",
            "building renovation and maintenance contracts",
            "infrastructure development municipal projects"
        ],
        "delivery": [
            "delivery and logistics services government agencies",
            "transportation services for medical supplies",
            "courier services for government documents"
        ],
        "general": [
            "office supplies and equipment procurement",
            "professional consulting services government"
        ]
    }
    validation_results = {
        "validation_timestamp": datetime.now().isoformat(),
        "index_stats": stats,
        "query_results": {},
        "performance_metrics": {},
        "quality_assessment": {}
    }
    print("\n3. Testing Retrieval by Sector:")
    total_queries = 0
    total_retrieval_time = 0
    semantic_relevance_scores = []
    for sector, queries in test_cases.items():
        print(f"\n   --- {sector.upper()} SECTOR ---")
        sector_results = []
        for query in queries:
            print(f"\n   Query: {query}")
            # Test retrieval with timing
            start_time = time.time()
            results = rag.retrieve(query, k=5, category_filter=sector if sector != 'general' else None)
            retrieval_time = time.time() - start_time
            total_queries += 1
            total_retrieval_time += retrieval_time
            print(f"   Retrieval time: {retrieval_time:.3f}s | Results: {len(results)}")
            # Analyze results
            if results:
                # Check semantic relevance (basic keyword matching)
                query_keywords = set(query.lower().split())
                for i, result in enumerate(results[:3]):  # Top 3 results
                    result_text = result.get('chunk_text', '').lower()
                    title = result.get('title', '').lower()
                    # Calculate rough semantic relevance
                    text_keywords = set(result_text.split())
                    title_keywords = set(title.split())
                    all_result_keywords = text_keywords.union(title_keywords)
                    keyword_overlap = len(query_keywords.intersection(all_result_keywords))
                    relevance_score = keyword_overlap / len(query_keywords) if query_keywords else 0
                    semantic_relevance_scores.append(relevance_score)
                    print(f"     {i+1}. Score: {result['similarity_score']:.3f} | "
                          f"Relevance: {relevance_score:.2f} | "
                          f"Category: {result.get('category', 'N/A')} | "
                          f"Title: {result.get('title', 'N/A')[:50]}...")
                sector_results.append({
                    "query": query,
                    "retrieval_time": retrieval_time,
                    "num_results": len(results),
                    "top_results": results[:3]
                })
            else:
                print("     No results found!")
                sector_results.append({
                    "query": query,
                    "retrieval_time": retrieval_time,
                    "num_results": 0,
                    "top_results": []
                })
        validation_results["query_results"][sector] = sector_results
    # Calculate performance metrics
    avg_retrieval_time = total_retrieval_time / total_queries if total_queries > 0 else 0
    avg_semantic_relevance = sum(semantic_relevance_scores) / len(semantic_relevance_scores) if semantic_relevance_scores else 0
    performance_metrics = {
        "total_queries_tested": total_queries,
        "average_retrieval_time_ms": avg_retrieval_time * 1000,
        "average_semantic_relevance": avg_semantic_relevance,
        "index_load_time_seconds": load_time
    }
    validation_results["performance_metrics"] = performance_metrics
    print(f"\n4. Performance Summary:")
    print(f"   Total queries tested: {total_queries}")
    print(f"   Average retrieval time: {avg_retrieval_time*1000:.1f}ms")
    print(f"   Average semantic relevance: {avg_semantic_relevance:.3f}")
    print(f"   Index load time: {load_time:.2f}s")
    # Quality assessment
    retrieval_success_rate = sum(1 for sector_results in validation_results["query_results"].values() 
                                for result in sector_results if result["num_results"] > 0) / total_queries
    quality_assessment = {
        "retrieval_success_rate": retrieval_success_rate,
        "meets_speed_requirement": avg_retrieval_time < 0.5,  # < 500ms
        "meets_relevance_threshold": avg_semantic_relevance > 0.3,  # Basic relevance
        "index_health": {
            "vectors_indexed": stats.get("total_vectors", 0),
            "categories_covered": len(stats.get("category_distribution", {})),
            "index_size_adequate": stats.get("total_vectors", 0) > 1000
        }
    }
    validation_results["quality_assessment"] = quality_assessment
    print(f"\n5. Quality Assessment:")
    print(f"   Retrieval success rate: {retrieval_success_rate:.1%}")
    print(f"   Speed requirement met: {quality_assessment['meets_speed_requirement']}")
    print(f"   Relevance threshold met: {quality_assessment['meets_relevance_threshold']}")
    print(f"   Index vectors: {quality_assessment['index_health']['vectors_indexed']:,}")
    print(f"   Categories covered: {quality_assessment['index_health']['categories_covered']}")
    # Save validation report
    report_path = "/app/government_rfp_bid_1927/analysis/rag_validation_report.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(validation_results, f, indent=2)
    print(f"\n6. Validation Report Saved: {report_path}")
    # Overall validation result
    overall_success = (
        quality_assessment["meets_speed_requirement"] and
        quality_assessment["meets_relevance_threshold"] and
        quality_assessment["index_health"]["index_size_adequate"] and
        retrieval_success_rate > 0.8
    )
    print(f"\n=== VALIDATION RESULT: {'SUCCESS' if overall_success else 'NEEDS IMPROVEMENT'} ===")
    return overall_success, validation_results
if __name__ == "__main__":
    success, results = comprehensive_rag_validation()
    if success:
        print("\nRAG system validation PASSED all requirements.")
    else:
        print("\nRAG system validation FAILED some requirements.")
        print("Check the detailed report for improvement areas.")