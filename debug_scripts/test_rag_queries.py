import sys
import os
import json
sys.path.append('/app/government_rfp_bid_1927/src')
from rag.rag_engine import search_rfps
def test_sample_queries():
    """Test RAG system with representative queries"""
    print("=== RAG System Sample Query Testing ===\n")
    # Representative queries for each sector
    queries = [
        ("bottled water delivery for office buildings", "bottled_water"),
        ("construction project management services", "construction"), 
        ("courier and delivery services", "delivery"),
        ("facilities maintenance and repair", None)  # General query
    ]
    for query, category in queries:
        print(f"Query: '{query}'")
        if category:
            print(f"Category Filter: {category}")
        try:
            results = search_rfps(query, k=3, category=category)
            print(f"Results Found: {len(results)}")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Similarity: {result['similarity_score']:.3f}")
                print(f"     Category: {result.get('category', 'N/A')}")
                print(f"     Title: {result.get('title', 'N/A')[:60]}...")
                print(f"     Agency: {result.get('agency', 'N/A')}")
                print(f"     Award Amount: ${result.get('award_amount', 0):,}")
                print(f"     Text Preview: {result.get('chunk_text', 'N/A')[:100]}...")
                print()
        except Exception as e:
            print(f"Error processing query: {e}")
        print("-" * 80)
        print()
if __name__ == "__main__":
    test_sample_queries()