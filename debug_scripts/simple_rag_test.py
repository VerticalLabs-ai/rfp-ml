import sys

sys.path.append('/app/government_rfp_bid_1927/src')
from rag.rag_engine import OptimizedRAGEngine


def test_rag_basic():
    """Basic test of RAG functionality"""
    print("=== RAG System Basic Test ===\n")
    # Initialize RAG
    rag = OptimizedRAGEngine()
    # Load existing index
    print("Loading RAG index...")
    if not rag.load_index():
        print("Failed to load index")
        return False
    # Get stats
    stats = rag.get_index_stats()
    print("Index loaded successfully!")
    print(f"Total vectors: {stats.get('total_vectors', 0):,}")
    print(f"Categories: {list(stats.get('category_distribution', {}).keys())}")
    # Test sample queries
    test_queries = [
        ("bottled water delivery", "bottled_water"),
        ("construction services", "construction"),
        ("courier delivery", "delivery"),
        ("office supplies", None)
    ]
    print("\n=== Testing Queries ===")
    for query, category in test_queries:
        print(f"\nQuery: '{query}' (Category: {category})")
        try:
            results = rag.retrieve(query, k=3, category_filter=category)
            print(f"Results found: {len(results)}")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result['similarity_score']:.3f}")
                print(f"     Category: {result.get('category', 'N/A')}")
                print(f"     Title: {result.get('title', 'N/A')[:50]}...")
                print(f"     Agency: {result.get('agency', 'N/A')[:30]}...")
        except Exception as e:
            print(f"Error: {e}")
    print("\n=== RAG Test Complete ===")
    return True
if __name__ == "__main__":
    success = test_rag_basic()
    print(f"\nRAG Test Result: {'SUCCESS' if success else 'FAILED'}")
