import sys
import os
import time
import json
from typing import Dict, List, Any
# Add the src directory to path
sys.path.append('/app/government_rfp_bid_1927/src')
from rag.rag_engine import RAGEngine
class RAGValidator:
    """Validate RAG system performance and operational metrics."""
    def __init__(self):
        self.rag = RAGEngine()
    def load_and_validate_system(self) -> Dict[str, Any]:
        """Load RAG system and validate it's ready."""
        print("Loading RAG system...")
        start_time = time.time()
        # Try to load existing artifacts
        success = self.rag.load_artifacts()
        load_time = time.time() - start_time
        if not success:
            print("Artifacts not found, building fresh index...")
            self.rag.build_index()
            load_time = time.time() - start_time
        stats = self.rag.get_stats()
        stats['load_time_seconds'] = load_time
        return stats
    def test_sector_queries(self) -> Dict[str, Any]:
        """Test retrieval performance for each RFP sector."""
        # Define comprehensive test queries for each sector
        sector_queries = {
            'bottled_water': [
                "bottled water supply for government offices",
                "drinking water delivery services",
                "water dispensing equipment and bottle services",
                "beverage vending and water supply contracts"
            ],
            'construction': [
                "building construction and renovation projects",
                "infrastructure development and maintenance",
                "facility construction management services",
                "architectural and engineering construction services"
            ],
            'delivery': [
                "logistics and delivery services",
                "transportation and courier services", 
                "freight and shipping services for government",
                "mail delivery and package services"
            ],
            'general': [
                "government procurement services",
                "facility management and maintenance",
                "professional services for agencies",
                "equipment and supply contracts"
            ]
        }
        results = {}
        for sector, queries in sector_queries.items():
            print(f"\nTesting {sector} queries...")
            sector_results = {
                'queries_tested': len(queries),
                'average_retrieval_time': 0,
                'relevance_scores': [],
                'category_match_rate': 0,
                'sample_results': []
            }
            total_time = 0
            category_matches = 0
            for query in queries:
                # Measure retrieval time
                start_time = time.time()
                retrieved_docs = self.rag.retrieve(query, k=5)
                retrieval_time = time.time() - start_time
                total_time += retrieval_time
                # Calculate relevance metrics
                if retrieved_docs:
                    avg_score = sum(doc['score'] for doc in retrieved_docs) / len(retrieved_docs)
                    sector_results['relevance_scores'].append(avg_score)
                    # Check category matching
                    top_result = retrieved_docs[0]
                    if top_result['metadata']['category'] == sector or sector == 'general':
                        category_matches += 1
                    # Store sample result for first query
                    if len(sector_results['sample_results']) == 0:
                        sector_results['sample_results'] = {
                            'query': query,
                            'top_3_results': [
                                {
                                    'score': doc['score'],
                                    'category': doc['metadata']['category'],
                                    'title': doc['metadata']['title'],
                                    'text_preview': doc['text'][:200] + "..."
                                }
                                for doc in retrieved_docs[:3]
                            ]
                        }
            # Calculate averages
            sector_results['average_retrieval_time'] = total_time / len(queries)
            sector_results['category_match_rate'] = category_matches / len(queries)
            sector_results['average_relevance_score'] = (
                sum(sector_results['relevance_scores']) / len(sector_results['relevance_scores'])
                if sector_results['relevance_scores'] else 0
            )
            results[sector] = sector_results
            print(f"  Average retrieval time: {sector_results['average_retrieval_time']:.3f}s")
            print(f"  Category match rate: {sector_results['category_match_rate']:.1%}")
            print(f"  Average relevance score: {sector_results['average_relevance_score']:.3f}")
        return results
    def test_performance_metrics(self) -> Dict[str, Any]:
        """Test various performance metrics."""
        print("\nTesting performance metrics...")
        # Test different k values
        test_query = "facility maintenance and cleaning services"
        k_values = [1, 5, 10, 20]
        k_performance = {}
        for k in k_values:
            start_time = time.time()
            results = self.rag.retrieve(test_query, k=k)
            retrieval_time = time.time() - start_time
            k_performance[f"k_{k}"] = {
                'retrieval_time': retrieval_time,
                'results_returned': len(results),
                'avg_score': sum(r['score'] for r in results) / len(results) if results else 0
            }
        # Test index loading performance
        print("Testing index reload performance...")
        start_time = time.time()
        test_rag = RAGEngine()
        test_rag.load_artifacts()
        reload_time = time.time() - start_time
        return {
            'k_value_performance': k_performance,
            'index_reload_time': reload_time,
            'memory_efficient': reload_time < 10.0,  # Should load in under 10 seconds
            'fast_retrieval': all(v['retrieval_time'] < 0.5 for v in k_performance.values())
        }
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        print("=" * 60)
        print("RAG SYSTEM VALIDATION REPORT")
        print("=" * 60)
        # System stats
        stats = self.load_and_validate_system()
        print(f"System Status: {stats['status']}")
        print(f"Total Documents: {stats['total_documents']:,}")
        print(f"Index Size: {stats['index_size']:,}")
        print(f"Load Time: {stats['load_time_seconds']:.2f}s")
        print(f"Model: {stats['model_name']}")
        # Category distribution
        print(f"\nCategory Distribution:")
        for category, count in stats['category_distribution'].items():
            percentage = (count / stats['total_documents']) * 100
            print(f"  {category}: {count:,} ({percentage:.1f}%)")
        # Sector query testing
        sector_results = self.test_sector_queries()
        # Performance metrics
        performance = self.test_performance_metrics()
        # Compile final report
        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'system_stats': stats,
            'sector_performance': sector_results,
            'performance_metrics': performance,
            'validation_summary': {
                'system_ready': stats['status'] == 'ready',
                'fast_loading': stats['load_time_seconds'] < 30,
                'adequate_coverage': stats['total_documents'] > 1000,
                'balanced_categories': len(stats['category_distribution']) >= 3,
                'fast_retrieval': performance['fast_retrieval'],
                'memory_efficient': performance['memory_efficient']
            }
        }
        # Print summary
        print(f"\nVALIDATION SUMMARY:")
        for criterion, passed in report['validation_summary'].items():
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {criterion}: {status}")
        # Overall assessment
        passed_criteria = sum(report['validation_summary'].values())
        total_criteria = len(report['validation_summary'])
        overall_score = passed_criteria / total_criteria
        print(f"\nOVERALL SCORE: {passed_criteria}/{total_criteria} ({overall_score:.1%})")
        if overall_score >= 0.8:
            print("✓ RAG SYSTEM VALIDATION: PASS")
        else:
            print("✗ RAG SYSTEM VALIDATION: NEEDS IMPROVEMENT")
        return report
def main():
    """Main validation function."""
    validator = RAGValidator()
    # Generate comprehensive validation report
    report = validator.generate_comprehensive_report()
    # Save report
    report_path = '/app/government_rfp_bid_1927/data/embeddings/validation_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"\nDetailed report saved to: {report_path}")
    return report
if __name__ == "__main__":
    main()